from app.database.db import db
from app.models.publishing_target import PublishingTarget
from app.services.accounts_service import AccountsService


class TargetsService:
    PLATFORM_NAMES = {
        "facebook": "Facebook",
        "instagram": "Instagram",
        "telegram": "Telegram",
    }

    def __init__(self, accounts_service=None):
        self.accounts_service = accounts_service or AccountsService()

    def platforms(self):
        return ["All Platforms", "Facebook", "Instagram", "Telegram"]

    def targets(self, platform="All Platforms"):
        key = self._platform_key(platform)

        if key in (None, "facebook"):
            targets = [target.to_dict() for target in self._facebook_targets()]

            if key is None:
                targets.extend(self._telegram_targets())

            return targets

        if key == "telegram":
            return self._telegram_targets()

        return []

    def placeholder_message(self, platform):
        key = self._platform_key(platform)

        if key == "instagram":
            return "Not implemented"

        return ""

    def _facebook_targets(self):
        account = self.accounts_service.get_active_account()

        if account is None:
            return []

        rows = db.get_groups(account_id=account["id"])
        return [self._group_to_target(dict(row)) for row in rows]

    def _group_to_target(self, group):
        return PublishingTarget(
            id=group.get("id"),
            platform="facebook",
            account_id=group.get("account_id"),
            target_type="facebook_group",
            external_id=group.get("group_uid") or "",
            name=group.get("name") or "",
            url=group.get("url") or "",
            members_count=group.get("members_count") or 0,
            privacy=group.get("privacy") or "",
            category=group.get("category") or "",
            selected=bool(group.get("selected")),
            active=bool(group.get("active")),
            metadata={
                "members": group.get("members") or "",
                "can_post": bool(group.get("can_post")),
                "last_publish": group.get("last_publish") or "",
            },
            last_scan=group.get("last_scan") or "",
        )

    def _platform_key(self, label):
        if not label or label == "All Platforms":
            return None

        return str(label).strip().lower()

    def _telegram_targets(self):
        return [
            {
                "id": target.get("id"),
                "platform": "telegram",
                "account_id": target.get("account_id"),
                "target_type": target.get("target_type"),
                "external_id": target.get("external_id"),
                "name": target.get("name"),
                "url": target.get("url"),
                "members_count": target.get("member_count") or 0,
                "privacy": "",
                "category": target.get("status") or "",
                "selected": bool(target.get("selected")),
                "active": bool(target.get("active")),
                "metadata": target.get("metadata") or {},
                "last_scan": target.get("last_checked") or "",
            }
            for target in db.get_telegram_targets()
        ]
