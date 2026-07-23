import re

from app.services.groups_service import GroupsService


class GroupsController:
    """State, filtering, sorting, and actions for the groups page."""

    def __init__(self, service=None):
        self.service = service or GroupsService()
        self.groups = []
        self.filtered_groups = []
        self.filters = self.default_filters()
        self.sort_key = "name"
        self.sort_reverse = False
        self.account_id = None

    def default_filters(self):
        return {
            "search": "",
            "min_members": "",
            "max_members": "",
            "privacy": "All",
            "category": "All Categories",
            "selected": "All",
            "status": "All",
        }

    def load(self):
        account = self.service.active_facebook_account()
        new_account_id = account["id"] if account else None

        if new_account_id != self.account_id:
            self.account_id = new_account_id
            self.groups = []
            self.filtered_groups = []
            self.filters = self.default_filters()

        if self.account_id is None:
            self.groups = []
            self.filtered_groups = []
            return []

        self.groups = self.service.get_groups(self.account_id)
        return self.apply_filters(self.filters)

    def refresh(self):
        return self.load()

    def scan(self):
        self.groups = self.service.scan_groups()
        return self.apply_filters(self.filters)

    def analyze(self):
        self.groups = self.service.analyze_groups()
        return self.apply_filters(self.filters)

    def apply_filters(self, filters):
        self.filters = filters.copy()
        min_members = self._to_int(self.filters["min_members"])
        max_members = self._to_int(self.filters["max_members"])
        groups = self.service.get_groups(
            self.account_id,
            search=self.filters["search"],
            min_members=min_members,
            max_members=max_members,
            privacy=self.filters["privacy"],
            category=self.filters["category"],
            selection=self.filters["selected"],
            status=self.filters["status"],
        )

        self.filtered_groups = self._sort(groups)
        return self.filtered_groups

    def set_group_selected(self, group_id, selected):
        self.service.set_group_selected(group_id, self.account_id, selected)

        for group in self.groups:
            if group.get("id") == group_id:
                group["selected"] = int(selected)
                break

        self.groups = self.service.get_groups(self.account_id)
        return self.apply_filters(self.filters)

    def set_visible_selected(self, selected):
        self.service.set_visible_selected(
            self.account_id,
            [group["id"] for group in self.filtered_groups],
            selected,
        )
        self.groups = self.service.get_groups(self.account_id)
        return self.apply_filters(self.filters)

    def set_all_account_groups_selected(self, selected):
        self.service.set_all_account_groups_selected(self.account_id, selected)
        return self.load()

    def sort_by(self, key):
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = False

        self.filtered_groups = self._sort(self.filtered_groups)
        return self.filtered_groups

    def export_csv(self, path):
        self.service.export_csv(path, self.filtered_groups)

    def is_publishing(self):
        return self.service.accounts_service.is_publishing()

    def categories(self):
        return self.service.categories(self.account_id) if self.account_id else ["All Categories"]

    def summary(self):
        return self.service.get_group_summary(
            self.account_id,
            filtered_group_ids=[group["id"] for group in self.filtered_groups],
        )

    def _sort(self, groups):
        return sorted(
            groups,
            key=lambda group: self._sort_value(group, self.sort_key),
            reverse=self.sort_reverse,
        )

    def _sort_value(self, group, key):
        if key == "members_count":
            return self._members_count(group)

        value = group.get(key)

        if value is None:
            return ""

        return str(value).lower()

    def _members_count(self, group):
        value = group.get("members_count")

        if value:
            return self._to_int(value) or 0

        return self._to_int(group.get("members")) or 0

    def _to_int(self, value):
        if value in (None, ""):
            return None

        text = str(value).replace(",", "").strip().lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*([km]?)", text)

        if not match:
            return None

        number = float(match.group(1))
        suffix = match.group(2)

        if suffix == "k":
            number *= 1000
        elif suffix == "m":
            number *= 1000000

        return int(number)
