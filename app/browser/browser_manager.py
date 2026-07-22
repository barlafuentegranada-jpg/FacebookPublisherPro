from playwright.sync_api import sync_playwright
import os


class BrowserManager:

    def __init__(self):

        self.playwright = None
        self.context = None
        self.page = None

        self.profile_path = os.path.abspath("profiles/facebook")

    # ---------------------------------

    def start(self):

        if self.is_running():
            return

        print("Starting Playwright...")

        self.playwright = sync_playwright().start()

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=False,
            viewport={
                "width": 1400,
                "height": 900
            }
        )

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        print("Browser started successfully.")

    # ---------------------------------

    def is_running(self):

        try:

            if self.context is None:
                return False

            self.context.pages

            return True

        except:

            self.page = None
            self.context = None

            return False

    # ---------------------------------

    def get_page(self):

        if not self.is_running():

            self.start()

        return self.page

    # ---------------------------------

    def goto(self, url):

        page = self.get_page()

        page.goto(
            url,
            wait_until="domcontentloaded"
        )

    # ---------------------------------

    def refresh(self):

        self.get_page().reload()

    # ---------------------------------

    def stop(self):

        try:

            if self.context:
                self.context.close()

        except:
            pass

        try:

            if self.playwright:
                self.playwright.stop()

        except:
            pass

        self.playwright = None
        self.context = None
        self.page = None


browser = BrowserManager()