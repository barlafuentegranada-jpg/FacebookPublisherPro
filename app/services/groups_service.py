import csv
import re

from app.database.db import db
from app.services.accounts_service import AccountsService
from app.services.facebook_service import facebook


class GroupsService:
    """Groups page data access and existing action facade."""

    def __init__(self, accounts_service=None):
        self.accounts_service = accounts_service or AccountsService()

    def active_facebook_account(self):
        account = self.accounts_service.get_active_account()

        if account is None:
            return None

        if account.get("platform", "facebook") != "facebook":
            return None

        return account

    def get_groups(
        self,
        account_id,
        search=None,
        min_members=None,
        max_members=None,
        privacy=None,
        category=None,
        selection=None,
        status=None,
    ):
        if account_id is None:
            return []

        groups = [dict(group) for group in db.get_groups(account_id=account_id)]
        return [
            group
            for group in groups
            if self._matches(group, search, min_members, max_members, privacy, category, selection, status)
        ]

    def set_group_selected(self, group_id, account_id, selected):
        row = db.conn.execute(
            """
            SELECT id
            FROM groups
            WHERE id=? AND account_id=?
            """,
            (group_id, account_id),
        ).fetchone()

        if not row:
            raise ValueError("Group does not belong to the active Facebook account.")

        db.set_group_selected(group_id, selected)

    def set_visible_selected(self, account_id, filtered_group_ids, selected):
        ids = [int(group_id) for group_id in filtered_group_ids]

        if not ids:
            return

        placeholders = ",".join("?" for _ in ids)
        rows = db.conn.execute(
            f"""
            SELECT id
            FROM groups
            WHERE account_id=? AND id IN ({placeholders})
            """,
            [account_id, *ids],
        ).fetchall()
        verified_ids = [row["id"] for row in rows]

        for group_id in verified_ids:
            db.set_group_selected(group_id, selected)

    def set_all_account_groups_selected(self, account_id, selected):
        rows = db.get_groups(account_id=account_id)

        for group in rows:
            db.set_group_selected(group["id"], selected)

    def get_group_summary(self, account_id, filtered_group_ids=None):
        if account_id is None:
            return {
                "total_account_groups": 0,
                "filtered_groups": 0,
                "selected_account_groups": 0,
                "selected_visible_groups": 0,
                "public_groups": 0,
                "private_groups": 0,
            }

        all_groups = [dict(group) for group in db.get_groups(account_id=account_id)]
        filtered_ids = set(int(group_id) for group_id in filtered_group_ids or [])
        visible_groups = [group for group in all_groups if group["id"] in filtered_ids] if filtered_group_ids is not None else all_groups

        return {
            "total_account_groups": len(all_groups),
            "filtered_groups": len(visible_groups),
            "selected_account_groups": sum(1 for group in all_groups if group.get("selected")),
            "selected_visible_groups": sum(1 for group in visible_groups if group.get("selected")),
            "public_groups": sum(1 for group in all_groups if str(group.get("privacy") or "").lower() == "public"),
            "private_groups": sum(1 for group in all_groups if str(group.get("privacy") or "").lower() == "private"),
        }

    def categories(self, account_id):
        values = {
            str(dict(group).get("category") or "").strip()
            for group in db.get_groups(account_id=account_id)
            if str(dict(group).get("category") or "").strip()
        }
        return ["All Categories"] + sorted(values)

    def refresh_groups(self):
        account = self.active_facebook_account()
        return self.get_groups(account["id"]) if account else []

    def scan_groups(self):
        if self.active_facebook_account() is None:
            raise RuntimeError("Select an active Facebook account before scanning groups.")

        account = self.accounts_service.ensure_active_browser()
        result = facebook.scan_groups(account_id=account["id"])

        if not result.get("success"):
            raise RuntimeError(result.get("message") or "Group scan failed.")

        return self.get_groups(account["id"])

    def analyze_groups(self):
        if self.active_facebook_account() is None:
            raise RuntimeError("Select an active Facebook account before analyzing groups.")

        account = self.accounts_service.ensure_active_browser()
        result = facebook.analyze_groups(account_id=account["id"])

        if not result.get("success"):
            raise RuntimeError(result.get("message") or "Group analysis failed.")

        return self.get_groups(account["id"])

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

    def _matches(self, group, search, min_members, max_members, privacy, category, selection, status):
        name = str(group.get("name") or "")
        members_text = str(group.get("members") or "")
        privacy_value = str(group.get("privacy") or "").strip()
        category_value = str(group.get("category") or "").strip()
        is_selected = bool(group.get("selected"))
        members_count = self._members_count(group)
        can_post = group.get("can_post")

        if search and str(search).strip().lower() not in " ".join([name, members_text, privacy_value, category_value]).lower():
            return False

        if min_members not in (None, "") and members_count < int(min_members):
            return False

        if max_members not in (None, "") and members_count > int(max_members):
            return False

        if privacy and privacy != "All":
            if privacy == "Unknown":
                if privacy_value:
                    return False
            elif privacy_value.lower() != privacy.lower():
                return False

        if category and category != "All Categories" and category_value != category:
            return False

        if selection == "Selected Only" and not is_selected:
            return False

        if selection == "Unselected Only" and is_selected:
            return False

        if status == "Active" and not bool(group.get("active")):
            return False

        if status == "Cannot Post" and bool(can_post):
            return False

        if status == "Unknown" and can_post is not None:
            return False

        return True

    def _members_count(self, group):
        value = group.get("members_count")

        if value:
            return int(value or 0)

        text = str(group.get("members") or "").replace(",", "").strip().lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*([km]?)", text)

        if not match:
            return 0

        number = float(match.group(1))
        suffix = match.group(2)

        if suffix == "k":
            number *= 1000
        elif suffix == "m":
            number *= 1000000

        return int(number)
