from app.browser.browser_manager import browser


class FacebookService:

    def _ensure_browser(self):

        if not browser.is_running():
            raise RuntimeError("No active account browser is running.")

    def login(self):

        self._ensure_browser()

        return browser.goto(
            "https://www.facebook.com/groups/feed/"
        )

    def scan_groups(self, account_id=None):

        self._ensure_browser()

        return browser.scan_groups(account_id=account_id)

    def analyze_groups(self, account_id=None):
        """Analyze all saved groups."""

        self._ensure_browser()

        return browser.analyze_groups(account_id=account_id)


facebook = FacebookService()
