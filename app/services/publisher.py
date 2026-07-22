from app.browser.browser_manager import browser
from app.database.db import db
from app.services.post_service import post_service


class Publisher:

    def __init__(self):
        self.running = False

    # =========================================

    def publish(self):

        if self.running:
            print("Publisher already running.")
            return

        if not post_service.is_ready():
            print("Nothing to publish.")
            return

        self.running = True

        try:

            page = browser.get_page()

            groups = db.get_selected_groups()

            print("=" * 60)
            print("Publisher Started")
            print("=" * 60)

            print(post_service.to_dict())

            print()

            print(f"Selected Groups: {len(groups)}")

            for group in groups:

                print("--------------------------------")

                print(group["name"])

                print(group["url"])

                # المرحلة الحالية:
                # فقط افتح الجروب

                page.goto(
                    group["url"],
                    wait_until="domcontentloaded"
                )

                page.wait_for_timeout(2000)

            print()

            print("Publisher Finished")

        finally:

            self.running = False


publisher = Publisher()