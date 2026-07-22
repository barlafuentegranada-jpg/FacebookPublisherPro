import csv

from app.database.db import db
from app.services.accounts_service import AccountsService
from app.services.facebook_service import facebook


class GroupsService:
    """Groups page data access and existing action facade."""

    def __init__(self, accounts_service=None):
        self.accounts_service = accounts_service or AccountsService()

    def get_groups(self):
        account = self.accounts_service.get_active_account()

        if account is None:
            return []

        return [dict(group) for group in db.get_groups(account_id=account["id"])]

    def set_selected(self, group_id, selected):
        db.set_group_selected(group_id, selected)

    def set_all_selected(self, selected):
        for group in self.get_groups():
            self.set_selected(group["id"], selected)

    def refresh_groups(self):
        return self.get_groups()

    def scan_groups(self):
        account = self.accounts_service.ensure_active_browser()
        result = facebook.scan_groups(account_id=account["id"])

        if not result.get("success"):
            raise RuntimeError(result.get("message") or "Group scan failed.")

        return self.get_groups()

    def analyze_groups(self):
        account = self.accounts_service.ensure_active_browser()
        result = facebook.analyze_groups(account_id=account["id"])

        if not result.get("success"):
            raise RuntimeError(result.get("message") or "Group analysis failed.")

        return self.get_groups()

    def export_csv(self, path, groups):
        fieldnames = [
            "id",
            "name",
            "url",
            "members",
            "members_count",
            "privacy",
            "category",
            "selected",
            "last_scan",
            "active",
            "can_post",
        ]

        with open(path, "w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(groups)
