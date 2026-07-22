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

    def __init__(self):
        self.state_path = Path("config/accounts_state.json")
        self.profiles_root = Path("profiles/accounts")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.profiles_root.mkdir(parents=True, exist_ok=True)

    def list_accounts(self):
        rows = db.conn.execute(
            """
            SELECT id, name, profile_path, created_at
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
            account["login_status"] = status.get("login_status", self.STATUS_LOGIN_REQUIRED)
            account["last_login"] = status.get("last_login", "")
            account["groups_count"] = self.groups_count(account["id"])
            accounts.append(account)

        return accounts

    def add_account(self, name):
        clean_name = name.strip()

        if not clean_name:
            raise ValueError("Account name is required.")

        cursor = db.conn.execute(
            """
            INSERT INTO accounts(name, profile_path)
            VALUES(?, ?)
            """,
            (clean_name, ""),
        )
        account_id = cursor.lastrowid
        profile_path = self._profile_path(account_id)
        profile_path.mkdir(parents=True, exist_ok=True)

        db.conn.execute(
            """
            UPDATE accounts
            SET profile_path=?
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
            SET name=?
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

        if browser.is_running() and browser_state.get("account_id") == account["id"]:
            browser.close()

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
            SELECT id, name, profile_path, created_at
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
        account["login_status"] = status.get("login_status", self.STATUS_LOGIN_REQUIRED)
        account["last_login"] = status.get("last_login", "")
        account["groups_count"] = self.groups_count(account["id"])
        return account

    def get_active_account(self):
        active_id = self._read_state().get("active_account_id")

        if active_id is None:
            return None

        return self.get_account(active_id)

    def set_active(self, account_id):
        if self.get_account(account_id) is None:
            raise ValueError("Account not found.")

        state = self._read_state()
        state["active_account_id"] = account_id
        self._write_state(state)
        return self.get_account(account_id)

    def open_facebook_login(self, account_id=None):
        return self.open_manual_login(account_id)

    def open_manual_login(self, account_id=None):
        account = self._account_or_active(account_id)

        if browser.is_running():
            result = browser.close()
            self._ensure_success(result)

        manual_login_browser.open(account["profile_path"])
        self.set_active(account["id"])
        return account, "Manual login opened"

    def open_browser(self, account_id=None):
        account = self._account_or_active(account_id)
        state = browser.get_state()

        if browser.is_running() and state.get("account_id") != account["id"]:
            result = browser.close()
            self._ensure_success(result)

        if not browser.is_running() and manual_login_browser.is_profile_in_use(account["profile_path"]):
            raise RuntimeError(manual_login_browser.PROFILE_LOCK_MESSAGE)

        result = browser.start_account(account)
        self._ensure_success(result)
        self.set_active(account["id"])
        return account, browser.get_state()

    def refresh_status(self, account_id=None):
        return self.check_login(account_id)

    def check_login(self, account_id=None):
        account = self._account_or_active(account_id)

        state = browser.get_state()

        if browser.is_running() and state.get("account_id") != account["id"]:
            result = browser.close()
            self._ensure_success(result)

        if not browser.is_running() and manual_login_browser.is_profile_in_use(account["profile_path"]):
            raise RuntimeError(manual_login_browser.PROFILE_LOCK_MESSAGE)

        if not browser.is_running():
            result = browser.start_account(account)
            self._ensure_success(result)

        self.set_active(account["id"])
        status = self.detect_login_status(account["id"], navigate=True)
        return account, status

    def detect_login_status(self, account_id=None, navigate=False):
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
        publish_attempts = db.conn.execute("SELECT COUNT(*) FROM publish_history").fetchone()[0]

        return {
            "total_accounts": len(accounts),
            "logged_in_accounts": sum(
                1 for account in accounts if account["login_status"] == self.STATUS_LOGGED_IN
            ),
            "total_groups": db.count_groups(),
            "selected_groups": db.count_selected_groups(),
            "publish_attempts": publish_attempts,
            "total_posts": db.count_posts(),
            "draft_posts": db.count_posts(status="Draft"),
            "ready_posts": db.count_posts(status="Ready"),
            "account_group_counts": [
                dict(row) for row in db.get_account_group_counts()
            ],
        }

    def browser_status(self):
        state = browser.get_state()
        return "Running" if state["running"] else "Closed"

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
        account = self.require_active_account()
        state = browser.get_state()

        if browser.is_running() and state.get("account_id") != account["id"]:
            result = browser.close()
            self._ensure_success(result)

        if not browser.is_running() and manual_login_browser.is_profile_in_use(account["profile_path"]):
            raise RuntimeError(manual_login_browser.PROFILE_LOCK_MESSAGE)

        result = browser.start_account(account)
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

        if status == self.STATUS_LOGGED_IN:
            entry["last_login"] = db.conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]

        self._write_state(state)

    def _ensure_success(self, result):
        if not result.get("success"):
            raise RuntimeError(result.get("message") or "Browser operation failed.")

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
