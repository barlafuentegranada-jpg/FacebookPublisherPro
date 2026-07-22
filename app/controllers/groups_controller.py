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

    def default_filters(self):
        return {
            "search": "",
            "min_members": "",
            "max_members": "",
            "privacy": "All",
            "category": "All Categories",
            "selected": "All",
        }

    def load(self):
        self.groups = self.service.refresh_groups()
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
        search = self.filters["search"].strip().lower()
        privacy = self.filters["privacy"]
        category = self.filters["category"]
        selected = self.filters["selected"]
        min_members = self._to_int(self.filters["min_members"])
        max_members = self._to_int(self.filters["max_members"])

        groups = []

        for group in self.groups:
            name = str(group.get("name") or "")
            members_text = str(group.get("members") or "")
            privacy_value = str(group.get("privacy") or "")
            category_value = str(group.get("category") or "")
            is_selected = bool(group.get("selected"))
            members_count = self._members_count(group)

            if search and search not in " ".join([name, members_text, privacy_value, category_value]).lower():
                continue

            if min_members is not None and members_count < min_members:
                continue

            if max_members is not None and members_count > max_members:
                continue

            if privacy != "All" and privacy_value.lower() != privacy.lower():
                continue

            if category != "All Categories" and category_value != category:
                continue

            if selected == "Selected Only" and not is_selected:
                continue

            if selected == "Unselected Only" and is_selected:
                continue

            groups.append(group)

        self.filtered_groups = self._sort(groups)
        return self.filtered_groups

    def set_group_selected(self, group_id, selected):
        self.service.set_selected(group_id, selected)

        for group in self.groups:
            if group.get("id") == group_id:
                group["selected"] = int(selected)
                break

        return self.apply_filters(self.filters)

    def select_all(self):
        self.service.set_all_selected(True)
        return self.load()

    def unselect_all(self):
        self.service.set_all_selected(False)
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

    def categories(self):
        values = {
            str(group.get("category") or "").strip()
            for group in self.groups
            if str(group.get("category") or "").strip()
        }
        return ["All Categories"] + sorted(values)

    def summary(self):
        total = len(self.filtered_groups)
        selected = sum(1 for group in self.filtered_groups if group.get("selected"))
        public = sum(1 for group in self.filtered_groups if str(group.get("privacy") or "").lower() == "public")
        private = sum(1 for group in self.filtered_groups if str(group.get("privacy") or "").lower() == "private")

        return {
            "total": total,
            "selected": selected,
            "public": public,
            "private": private,
        }

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
