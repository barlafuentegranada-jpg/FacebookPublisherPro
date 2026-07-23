import json
import shutil
from pathlib import Path

from app.browser.manual_login_browser import manual_login_browser
from app.browser.browser_manager import browser
from app.database.db import db


class AccountsService:
    """Account persistence and browser-facing account operations."""

    STATUS_LOGIN_REQUIRED = "Login required"
    STATUS_2FA_REQUIRED = "Two-factor authentication required"
    STATUS_LOGGED_IN = "Logged in"
    STATUS_CHECKPOINT_REQUIRED = "Checkpoint required"
    STATUS_PAGE_LOAD_FAILED = "Page load failed"
    PUBLISHING_AVAILABLE = "Available"
    PUBLISHING_COOLING_DOWN = "CoolingDown"
    PUBLISHING_RATE_LIMITED = "RateLimited"
    PUBLISHING_MANUAL_REVIEW = "ManualReviewRequired"
    PUBLISHING_STATES = {
        PUBLISHING_AVAILABLE,
        PUBLISHING_COOLING_DOWN,
        PUBLISHING_RATE_LIMITED,
        PUBLISHING_MANUAL_REVIEW,
    }

    def __init__(self):
        self.state_path = Path("config/accounts_state.json")
        self.profiles_root = Path("profiles/accounts")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.profiles_root.mkdir(parents=True, exist_ok=True)

    def list_accounts(self):
        rows = db.conn.execute(
            """
            SELECT id, platform, name, profile_path, status, active, last_login,
                   publishing_state, publishing_state_updated_at, created_at, updated_at
            FROM accounts
            ORDER BY name
            """
        ).fetchall()
        state = self._read_state()
        active_id = state.get("active_account_id")
        statuses = state.get("statuses", {})
        accounts = []

        for row in rows:
            account = self._normalize_profile(dict(row))
            status = statuses.get(str(account["id"]), {})
            account["active"] = account["id"] == active_id
            account["login_status"] = status.get("login_status", account.get("status") or self.STATUS_LOGIN_REQUIRED)
            account["status"] = account["login_status"]
            account["last_login"] = status.get("last_login", account.get("last_login") or "")
            account["publishing_state"] = account.get("publishing_state") or self.PUBLISHING_AVAILABLE
            account["groups_count"] = self.groups_count(account["id"])
            accounts.append(account)

        return accounts

    def add_account(self, name, platform="facebook"):
        if platform != "facebook":
            raise ValueError("Coming in the next platform integration sprint.")

        clean_name = name.strip()

        if not clean_name:
            raise ValueError("Account name is required.")

        cursor = db.conn.execute(
            """
            INSERT INTO accounts(platform, name, profile_path, status, active, updated_at)
            VALUES(?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (platform, clean_name, "", self.STATUS_LOGIN_REQUIRED),
        )
        account_id = cursor.lastrowid
        profile_path = self._profile_path(account_id)
        profile_path.mkdir(parents=True, exist_ok=True)

        db.conn.execute(
            """
            UPDATE accounts
            SET profile_path=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (str(profile_path), account_id),
        )
        db.conn.commit()
        self._set_status(account_id, self.STATUS_LOGIN_REQUIRED)

        if self.get_active_account() is None:
            self.set_active(account_id)

        return self.get_account(account_id)

    def rename_account(self, account_id, name):
        clean_name = name.strip()

        if not clean_name:
            raise ValueError("Account name is required.")

        db.conn.execute(
            """
            UPDATE accounts
            SET name=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (clean_name, account_id),
        )
        db.conn.commit()
        return self.get_account(account_id)

    def remove_account(self, account_id):
        db.conn.execute(
            """
            DELETE FROM accounts
            WHERE id=?
            """,
            (account_id,),
        )
        db.conn.commit()

        state = self._read_state()
        state.setdefault("statuses", {}).pop(str(account_id), None)

        if state.get("active_account_id") == account_id:
            remaining = self.list_accounts()
            state["active_account_id"] = remaining[0]["id"] if remaining else None

        self._write_state(state)

    def reset_login_profile(self, account_id):
        account = self._account_or_active(account_id)
        browser_state = browser.get_state()

        if self._publishing_active(browser_state):
            raise RuntimeError("Publishing is running. Stop it before switching accounts or restarting the browser.")

        if browser.is_running() and browser_state.get("account_id") == account["id"]:
            browser.shutdown()

        profile_path = Path(account["profile_path"])
        backup_path = None

        if profile_path.exists():
            timestamp = db.conn.execute("SELECT strftime('%Y%m%d%H%M%S','now')").fetchone()[0]
            backup_path = profile_path.with_name(f"{profile_path.name}-backup-{timestamp}")
            profile_path.rename(backup_path)

        profile_path.mkdir(parents=True, exist_ok=True)
        self._set_status(account["id"], self.STATUS_LOGIN_REQUIRED)

        return {
            "account": self.get_account(account["id"]),
            "backup_path": str(backup_path) if backup_path else "",
        }

    def get_account(self, account_id):
        row = db.conn.execute(
            """
            SELECT id, platform, name, profile_path, status, active, last_login,
                   publishing_state, publishing_state_updated_at, created_at, updated_at
            FROM accounts
            WHERE id=?
            """,
            (account_id,),
        ).fetchone()

        if not row:
            return None

        state = self._read_state()
        account = self._normalize_profile(dict(row))
        status = state.get("statuses", {}).get(str(account_id), {})
        account["active"] = account["id"] == state.get("active_account_id")
        account["login_status"] = status.get("login_status", account.get("status") or self.STATUS_LOGIN_REQUIRED)
        account["status"] = account["login_status"]
        account["last_login"] = status.get("last_login", account.get("last_login") or "")
        account["publishing_state"] = account.get("publishing_state") or self.PUBLISHING_AVAILABLE
        account["groups_count"] = self.groups_count(account["id"])
        return account

    def mark_rate_limited(self, account_id, detection_time=None):
        account = self.get_account(account_id)

        if not account or account.get("platform", "facebook") != "facebook":
            raise ValueError("Facebook account not found.")

        db.set_account_publishing_state(
            account_id,
            self.PUBLISHING_RATE_LIMITED,
            updated_at=detection_time,
        )
        return self.get_account(account_id)

    def mark_available_after_review(self, account_id, confirmed=False):
        if not confirmed:
            raise ValueError("Confirm that Facebook allows posting before marking the account available.")

        account = self.get_account(account_id)

        if not account or account.get("platform", "facebook") != "facebook":
            raise ValueError("Facebook account not found.")

        db.set_account_publishing_state(account_id, self.PUBLISHING_AVAILABLE)
        return self.get_account(account_id)

    def require_publishing_available(self, account):
        state = account.get("publishing_state") or self.PUBLISHING_AVAILABLE

        if state != self.PUBLISHING_AVAILABLE:
            raise RuntimeError(
                f"Facebook publishing is disabled for this account ({state}). "
                "Review Facebook Account Status and Support Inbox, then use "
                "Mark Available After Review."
            )

        return account

    def get_active_account(self):
        active_id = self._read_state().get("active_account_id")

        if active_id is None:
            return None

        return self.get_account(active_id)

    def set_active(self, account_id):
        if browser.is_publishing():
            raise RuntimeError("Publishing is running. Stop it before switching accounts or restarting the browser.")

        if self.get_account(account_id) is None:
            raise ValueError("Account not found.")

        state = self._read_state()
        state["active_account_id"] = account_id
        self._write_state(state)
        db.conn.execute("UPDATE accounts SET active=0")
        db.conn.execute(
            """
            UPDATE accounts
            SET active=1,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (account_id,),
        )
        db.conn.commit()
        return self.get_account(account_id)

    def open_facebook_login(self, account_id=None):
        return self.open_manual_login(account_id)

    def open_manual_login(self, account_id=None):
        account = self._account_or_active(account_id)

        if self._publishing_active(browser.get_state()):
            raise RuntimeError("Publishing is running. Stop it before switching accounts or restarting the browser.")

        if browser.is_running():
            result = browser.shutdown()
            self._ensure_success(result)

        manual_login_browser.open(account["profile_path"])
        self.set_active(account["id"])
        return account, "Manual login opened"

    def open_browser(self, account_id=None):
        if browser.is_publishing():
            raise RuntimeError("Publishing is running. Stop it before switching accounts or restarting the browser.")

        account = self._account_or_active(account_id)
        state = browser.get_state()

        if (
            (not browser.is_running() or state.get("account_id") != account["id"])
            and manual_login_browser.is_profile_in_use(account["profile_path"])
        ):
            raise RuntimeError(manual_login_browser.PROFILE_LOCK_MESSAGE)

        result = browser.switch_account(account)
        self._ensure_success(result)
        self.set_active(account["id"])
        return account, browser.get_state()

    def refresh_status(self, account_id=None):
        return self.check_login(account_id)

    def check_login(self, account_id=None):
        if browser.is_publishing():
            raise RuntimeError("Publishing is running. Stop it before switching accounts or restarting the browser.")

        account = self._account_or_active(account_id)

        state = browser.get_state()

        if (
            (not browser.is_running() or state.get("account_id") != account["id"])
            and manual_login_browser.is_profile_in_use(account["profile_path"])
        ):
            raise RuntimeError(manual_login_browser.PROFILE_LOCK_MESSAGE)

        if not browser.is_running() or state.get("account_id") != account["id"]:
            result = browser.switch_account(account)
            self._ensure_success(result)

        self.set_active(account["id"])
        status = self.detect_login_status(account["id"], navigate=True)
        return account, status

    def detect_login_status(self, account_id=None, navigate=False):
        if browser.is_publishing():
            raise RuntimeError("Publishing is running. Stop it before switching accounts or restarting the browser.")

        account = self._account_or_active(account_id)

        result = browser.check_login()

        if not result.get("success"):
            status = self.STATUS_PAGE_LOAD_FAILED
        else:
            data = result.get("data") or {}
            url = str(data.get("url") or "").lower()
            has_login_form = bool(data.get("has_login_form"))
            status = self._status_from_markers(data, url, has_login_form)

        self._set_status(account["id"], status)
        return status

    def dashboard_stats(self):
        accounts = self.list_accounts()
        publish_stats = db.publish_stats()
        campaign_stats = db.campaign_stats()

        stats = {
            "total_accounts": len(accounts),
            "facebook_accounts": db.count_accounts(platform="facebook"),
            "instagram_accounts": db.count_accounts(platform="instagram"),
            "telegram_accounts": db.count_accounts(platform="telegram"),
            "logged_in_accounts": sum(
                1 for account in accounts if account["login_status"] == self.STATUS_LOGGED_IN
            ),
            "total_groups": db.count_groups(),
            "total_targets": db.count_targets(),
            "selected_groups": db.count_selected_groups(),
            "publish_attempts": publish_stats["attempts"],
            "successful_posts": publish_stats["successful"],
            "failed_posts": publish_stats["failed"],
            "rate_limited_attempts": db.count_publish_history(status="RateLimited"),
            "accounts_requiring_review": db.count_accounts_requiring_review(),
            "success_rate": publish_stats["success_rate"],
            "total_posts": db.count_posts(),
            "draft_posts": db.count_posts(status="Draft"),
            "ready_posts": db.count_posts(status="Ready"),
            "account_group_counts": [
                dict(row) for row in db.get_account_group_counts()
            ],
            "account_target_counts": self._dashboard_target_counts(),
            "recent_activity": db.get_publish_history()[:10],
        }
        stats.update(campaign_stats)
        return stats

    def _dashboard_target_counts(self):
        facebook_rows = db.conn.execute(
            """
            SELECT
                accounts.name AS account,
                'Facebook' AS platform,
                COUNT(groups.id) AS target_count,
                COALESCE(SUM(CASE WHEN groups.selected=1 THEN 1 ELSE 0 END), 0) AS selected_count
            FROM accounts
            LEFT JOIN groups ON groups.account_id=accounts.id
            WHERE LOWER(COALESCE(accounts.platform, 'facebook'))='facebook'
            GROUP BY accounts.id, accounts.name
            """
        ).fetchall()
        telegram_rows = db.conn.execute(
            """
            SELECT
                COALESCE(accounts.name, telegram_accounts.bot_username, 'Telegram Bot') AS account,
                'Telegram' AS platform,
                COUNT(telegram_targets.id) AS target_count,
                COALESCE(SUM(
                    CASE
                        WHEN telegram_targets.selected=1 AND telegram_targets.active=1 THEN 1
                        ELSE 0
                    END
                ), 0) AS selected_count
            FROM telegram_accounts
            LEFT JOIN accounts ON accounts.id=telegram_accounts.account_id
            LEFT JOIN telegram_targets ON telegram_targets.account_id=telegram_accounts.account_id
            GROUP BY telegram_accounts.account_id, accounts.name, telegram_accounts.bot_username
            """
        ).fetchall()
        return [dict(row) for row in list(facebook_rows) + list(telegram_rows)]

    def browser_status(self):
        state = browser.get_state()
        return "Running" if state["running"] else "Closed"

    def is_publishing(self):
        return browser.is_publishing()

    def shutdown_browser(self):
        return browser.shutdown()

    def groups_count(self, account_id):
        return db.count_groups(account_id=account_id)

    def require_active_account(self):
        account = self.get_active_account()

        if account is None:
            raise RuntimeError("No active Facebook account. Add or select an account first.")

        return account

    def ensure_active_browser(self):
        if browser.is_publishing():
            return self.require_active_account()

        account = self.require_active_account()
        state = browser.get_state()

        if (
            (not browser.is_running() or state.get("account_id") != account["id"])
            and manual_login_browser.is_profile_in_use(account["profile_path"])
        ):
            raise RuntimeError(manual_login_browser.PROFILE_LOCK_MESSAGE)

        if browser.is_running() and state.get("account_id") == account["id"]:
            result = {
                "success": True,
            }
        else:
            result = browser.switch_account(account)
            self._ensure_success(result)
        return account

    def _account_or_active(self, account_id=None):
        account = self.get_account(account_id) if account_id else self.get_active_account()

        if account is None:
            raise RuntimeError("No active Facebook account. Add or select an account first.")

        return account

    def _status_from_page(self, url, body, has_login_form=False):
        if "two_step_verification" in url or "two-factor" in body or "two factor" in body:
            return self.STATUS_2FA_REQUIRED

        if "checkpoint" in url or "checkpoint" in body:
            return self.STATUS_CHECKPOINT_REQUIRED

        if has_login_form:
            return self.STATUS_LOGIN_REQUIRED

        if self._looks_logged_out(url, body):
            return self.STATUS_LOGIN_REQUIRED

        if self._looks_logged_in(url, body):
            return self.STATUS_LOGGED_IN

        return self.STATUS_LOGIN_REQUIRED

    def _status_from_markers(self, markers, url, has_login_form=False):
        if markers.get("has_two_factor"):
            return self.STATUS_2FA_REQUIRED

        if markers.get("has_checkpoint"):
            return self.STATUS_CHECKPOINT_REQUIRED

        if has_login_form or markers.get("has_logged_out_marker"):
            return self.STATUS_LOGIN_REQUIRED

        if markers.get("has_logged_in_marker"):
            return self.STATUS_LOGGED_IN

        return self.STATUS_LOGIN_REQUIRED

    def _looks_logged_out(self, url, body):
        logged_out_markers = [
            "log in",
            "forgot password",
            "create new account",
            "facebook helps you connect",
            "password",
        ]

        return "login" in url or any(marker in body for marker in logged_out_markers)

    def _looks_logged_in(self, url, body):
        logged_in_markers = [
            "what's on your mind",
            "news feed",
            "marketplace",
            "groups",
            "messenger",
        ]

        return "facebook.com" in url and any(marker in body for marker in logged_in_markers)

    def _is_auth_flow_url(self, url):
        return (
            "two_step_verification" in url
            or "checkpoint" in url
            or "recover" in url
            or "login" in url
        )

    def _set_status(self, account_id, status):
        state = self._read_state()
        statuses = state.setdefault("statuses", {})
        entry = statuses.setdefault(str(account_id), {})
        entry["login_status"] = status

        last_login = None
        if status == self.STATUS_LOGGED_IN:
            last_login = db.conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
            entry["last_login"] = last_login

        db.conn.execute(
            """
            UPDATE accounts
            SET status=?,
                last_login=COALESCE(?, last_login),
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, last_login, account_id),
        )
        db.conn.commit()

        self._write_state(state)

    def _ensure_success(self, result):
        if not result.get("success"):
            raise RuntimeError(result.get("message") or "Browser operation failed.")

    def _publishing_active(self, state):
        return bool(state.get("publishing_active") or state.get("operation") == "publishing")

    def _read_state(self):
        if not self.state_path.exists():
            return {
                "active_account_id": None,
                "statuses": {},
            }

        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "active_account_id": None,
                "statuses": {},
            }

    def _write_state(self, state):
        self.state_path.write_text(
            json.dumps(state, indent=2),
            encoding="utf-8",
        )

    def _profile_path(self, account_id):
        return self.profiles_root / str(account_id)

    def _normalize_profile(self, account):
        expected_path = self._profile_path(account["id"])

        if account.get("profile_path") != str(expected_path):
            old_value = account.get("profile_path") or ""
            old_path = Path(old_value) if old_value else None

            if old_path and old_path.exists() and not expected_path.exists():
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(expected_path))
            else:
                expected_path.mkdir(parents=True, exist_ok=True)

            db.conn.execute(
                """
                UPDATE accounts
                SET profile_path=?
                WHERE id=?
                """,
                (str(expected_path), account["id"]),
            )
            db.conn.commit()
            account["profile_path"] = str(expected_path)

        return account
