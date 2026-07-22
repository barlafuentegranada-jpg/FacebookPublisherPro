from app.browser.browser_manager import browser
from app.services.group_scanner import scanner
from app.services.group_analyzer import analyzer


class FacebookService:

    def _ensure_browser(self):

        if not browser.is_running():
            browser.start()

    def login(self):

        self._ensure_browser()

        browser.goto(
            "https://www.facebook.com/groups/feed/"
        )

    def scan_groups(self):

        self._ensure_browser()

        scanner.scan()

    def analyze_groups(self):
        """Analyze all saved groups."""

        self._ensure_browser()

        analyzer.analyze()


facebook = FacebookService()