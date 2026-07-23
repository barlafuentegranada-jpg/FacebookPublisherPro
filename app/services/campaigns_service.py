import json

from app.database.db import db
from app.models.campaign import CAMPAIGN_STATUSES
from app.platforms import platform_registry
from app.services.accounts_service import AccountsService


class CampaignsService:
    CONNECTED_TELEGRAM = {"Connected"}
    CONNECTED_FACEBOOK = {AccountsService.STATUS_LOGGED_IN}

    def __init__(self, accounts_service=None):
        self.accounts_service = accounts_service or AccountsService()

    def campaigns(self):
        rows = db.get_campaigns()
        return [self._with_summary(row) for row in rows]

    def get(self, campaign_id):
        campaign = db.get_campaign(campaign_id)

        if not campaign:
            return None

        campaign["accounts"] = db.get_campaign_accounts(campaign_id, enabled=None)
        campaign["targets"] = db.get_campaign_targets(campaign_id, enabled=None)
        campaign["runs"] = db.get_campaign_runs(campaign_id)
        campaign["validation"] = self.validate(campaign_id)
        return self._with_summary(campaign)

    def create(self, name="New Campaign"):
        campaign = db.create_campaign(name=name.strip() or "New Campaign")
        return self.get(campaign["id"])

    def save(self, campaign_id, data):
        delay_min = self._to_int(data.get("delay_min_seconds"), "Minimum delay")
        delay_max = self._to_int(data.get("delay_max_seconds"), "Maximum delay")
        if delay_min < 0 or delay_max < 0 or delay_min > delay_max:
            raise ValueError("Delay values must be valid and minimum cannot exceed maximum.")

        db.update_campaign(
            campaign_id,
            name=(data.get("name") or "").strip(),
            description=data.get("description") or "",
            post_id=int(data["post_id"]) if data.get("post_id") else None,
            delay_min_seconds=delay_min,
            delay_max_seconds=delay_max,
            stop_on_error=bool(data.get("stop_on_error")),
            stop_on_checkpoint=bool(data.get("stop_on_checkpoint")),
            continue_other_platforms_after_facebook_rate_limit=bool(
                data.get("continue_other_platforms_after_facebook_rate_limit")
            ),
        )
        db.replace_campaign_accounts(campaign_id, data.get("accounts") or [])
        db.replace_campaign_targets(campaign_id, data.get("targets") or [])
        validation = self.validate(campaign_id)
        db.update_campaign(campaign_id, status="Ready" if validation["valid"] else "Draft")
        return self.get(campaign_id)

    def duplicate(self, campaign_id):
        duplicate = db.duplicate_campaign(campaign_id)
        return self.get(duplicate["id"]) if duplicate else None

    def delete(self, campaign_id):
        db.delete_campaign(campaign_id)

    def archive(self, campaign_id):
        return db.archive_campaign(campaign_id)

    def ready_posts(self):
        return db.get_ready_posts()

    def enabled_platforms(self):
        return [
            platform
            for platform in platform_registry.enabled_platforms()
            if platform["key"] in ("facebook", "telegram")
        ]

    def available_accounts(self):
        accounts = []

        for account in self.accounts_service.list_accounts():
            platform = account.get("platform") or "facebook"

            if platform not in ("facebook", "telegram"):
                continue

            connected = self._account_connected(account)
            accounts.append(
                {
                    "id": account["id"],
                    "platform": platform,
                    "name": account.get("name") or f"Account {account['id']}",
                    "status": account.get("status") or account.get("login_status") or "",
                    "publishing_state": account.get("publishing_state") or AccountsService.PUBLISHING_AVAILABLE,
                    "connected": connected,
                }
            )

        return accounts

    def available_targets(self, account_ids=None):
        account_filter = {int(value) for value in account_ids or []}
        targets = []

        for account in self.available_accounts():
            if account_filter and account["id"] not in account_filter:
                continue

            if not account["connected"]:
                continue

            if account["platform"] == "facebook":
                targets.extend(self._facebook_targets(account))
            elif account["platform"] == "telegram":
                targets.extend(self._telegram_targets(account))

        return sorted(targets, key=lambda row: (row["platform"], row["account_name"].lower(), row["name"].lower()))

    def validate(self, campaign_id):
        campaign = db.get_campaign(campaign_id)
        errors = []

        if not campaign:
            return {"valid": False, "errors": ["Campaign not found."]}

        if not (campaign.get("name") or "").strip():
            errors.append("Campaign name is required.")

        post = db.get_post(campaign.get("post_id")) if campaign.get("post_id") else None
        if not post or post.get("status") != "Ready":
            errors.append("Select a Ready post.")

        accounts = db.get_campaign_accounts(campaign_id)
        targets = db.get_campaign_targets(campaign_id)

        if not accounts:
            errors.append("Select at least one connected account.")

        if not targets:
            errors.append("Select at least one target.")

        account_keys = {(item["platform"], int(item["account_id"])) for item in accounts}
        for account in accounts:
            db_account = self._account_by_id(account["account_id"])
            if not db_account or not self._account_connected(db_account):
                if (
                    db_account
                    and account["platform"] == "facebook"
                    and db_account.get("publishing_state") != AccountsService.PUBLISHING_AVAILABLE
                ):
                    errors.append(
                        f"Facebook account {account['account_id']} requires review "
                        f"({db_account.get('publishing_state')})."
                    )
                else:
                    errors.append(f"{account['platform']} account {account['account_id']} is not connected.")

        for target in targets:
            key = (target["platform"], int(target["account_id"]))
            if key not in account_keys:
                errors.append(
                    f"{target['platform']} target {target['target_id']} does not belong to a selected account."
                )
                continue

            if not self._target_exists(target):
                errors.append(f"{target['platform']} target {target['target_id']} is unavailable.")

        if int(campaign.get("delay_min_seconds") or 0) < 0:
            errors.append("Minimum delay cannot be negative.")

        if int(campaign.get("delay_max_seconds") or 0) < int(campaign.get("delay_min_seconds") or 0):
            errors.append("Maximum delay must be greater than or equal to minimum delay.")

        if post:
            for platform in sorted({account["platform"] for account in accounts}):
                if not platform_registry.is_enabled(platform):
                    errors.append(f"{platform} is not enabled.")
                    continue

                adapter = platform_registry.get(platform)
                result = adapter.validate_post(post)
                if not result.get("success"):
                    errors.append(f"{adapter.platform_name}: {result.get('message') or 'Post is not supported.'}")

                media_error = self._capability_error(platform, post)
                if media_error:
                    errors.append(media_error)

        return {"valid": not errors, "errors": errors}

    def runs(self, campaign_id=None):
        return db.get_campaign_runs(campaign_id)

    def statuses(self):
        return CAMPAIGN_STATUSES

    def stats(self):
        return db.campaign_stats()

    def _with_summary(self, campaign):
        accounts = db.get_campaign_accounts(campaign["id"])
        targets = db.get_campaign_targets(campaign["id"])
        runs = db.get_campaign_runs(campaign["id"])
        latest = runs[0] if runs else None
        success_rate = 0

        if latest:
            attempts = latest["success_count"] + latest["failed_count"] + latest["skipped_count"]
            success_rate = round((latest["success_count"] / attempts) * 100, 1) if attempts else 0

        campaign.update(
            {
                "platforms_summary": ", ".join(sorted({item["platform"] for item in accounts})) or "-",
                "accounts_count": len(accounts),
                "targets_count": len(targets),
                "last_run": latest.get("started_at") if latest else "",
                "success_rate": success_rate,
            }
        )
        return campaign

    def _facebook_targets(self, account):
        return [
            {
                "platform": "facebook",
                "account_id": account["id"],
                "account_name": account["name"],
                "target_id": row["id"],
                "name": row["name"] or f"Group {row['id']}",
                "selected": bool(row["selected"]),
                "enabled": bool(row["selected"]),
                "can_post": bool(row["can_post"]),
            }
            for row in db.get_selected_groups(account_id=account["id"])
            if row["active"]
        ]

    def _telegram_targets(self, account):
        return [
            {
                "platform": "telegram",
                "account_id": account["id"],
                "account_name": account["name"],
                "target_id": target["id"],
                "name": target.get("name") or target.get("username") or target.get("external_id"),
                "selected": bool(target.get("selected")),
                "enabled": bool(target.get("selected")),
                "can_post": bool(target.get("can_post")),
            }
            for target in db.get_telegram_targets(account_id=account["id"])
            if target.get("active")
        ]

    def _account_by_id(self, account_id):
        for account in self.accounts_service.list_accounts():
            if int(account["id"]) == int(account_id):
                return account
        return None

    def _account_connected(self, account):
        platform = account.get("platform") or "facebook"
        status = account.get("status") or account.get("login_status") or ""

        if platform == "telegram":
            return status in self.CONNECTED_TELEGRAM

        if platform == "facebook":
            return (
                status in self.CONNECTED_FACEBOOK
                and account.get("publishing_state", AccountsService.PUBLISHING_AVAILABLE)
                == AccountsService.PUBLISHING_AVAILABLE
            )

        return False

    def _target_exists(self, target):
        if target["platform"] == "facebook":
            row = db.conn.execute(
                """
                SELECT id
                FROM groups
                WHERE id=? AND account_id=? AND active=1
                """,
                (target["target_id"], target["account_id"]),
            ).fetchone()
            return row is not None

        if target["platform"] == "telegram":
            row = db.get_telegram_target(target["target_id"])
            return bool(row and int(row["account_id"]) == int(target["account_id"]) and row.get("active"))

        return False

    def _capability_error(self, platform, post):
        capabilities = platform_registry.capabilities(platform)
        has_image = bool(post.get("image_path"))
        has_video = bool(post.get("video_path"))

        if has_image and not capabilities.supports_images:
            return f"{platform} does not support image posts."

        if has_video and not capabilities.supports_video:
            return f"{platform} does not support video posts."

        return ""

    def _to_int(self, value, label):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a whole number.")
