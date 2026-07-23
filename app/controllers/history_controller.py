from app.services.history_service import HistoryService


class HistoryController:
    def __init__(self, service=None):
        self.service = service or HistoryService()
        self.platform_filter = "All"
        self.account_filter = "All"
        self.status_filter = "All"
        self.date_filter = ""
        self.campaign_filter = "All"

    def accounts(self):
        return self.service.accounts()

    def statuses(self):
        return self.service.STATUSES

    def campaigns(self):
        return self.service.campaigns()

    def platforms(self):
        return self.service.platforms()

    def load(self):
        account_id = self._account_id(self.account_filter)
        return self.service.history(
            account_id=account_id,
            status=self.status_filter,
            date=self.date_filter.strip(),
            platform=self.platform_filter,
            campaign_id=self._campaign_id(self.campaign_filter),
        )

    def set_filters(self, platform_filter, account_filter, status_filter, date_filter, campaign_filter="All"):
        self.platform_filter = platform_filter
        self.account_filter = account_filter
        self.status_filter = status_filter
        self.date_filter = date_filter
        self.campaign_filter = campaign_filter
        return self.load()

    def _account_id(self, value):
        if not value or value == "All":
            return None

        return int(value.split("|", 1)[0].strip())

    def _campaign_id(self, value):
        if not value or value == "All":
            return None

        return int(value.split("|", 1)[0].strip())
