from playwright.sync_api import TimeoutError

from app.database.db import db


class GroupScanner:

    def scan(self):
        from app.browser.browser_manager import browser

        return browser.scan_groups()

    def scan_page(self, page, account_id=None):
        if account_id is None:
            raise RuntimeError("An active account is required before scanning groups.")

        print("Opening Groups page...")

        if "facebook.com/groups" not in page.url:

            page.goto(
                "https://www.facebook.com/groups/feed/",
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(3000)

        else:
            page.wait_for_timeout(2000)

        # =====================================
        # Open "See all"
        # =====================================

        try:

            print("Looking for 'See all'...")

            page.get_by_role(
                "link",
                name="See all"
            ).click(timeout=5000)

            page.wait_for_timeout(3000)

            print("Opened See all")

        except TimeoutError:

            print("'See all' button not found.")

        except Exception as e:

            print(e)

        # =====================================
        # Scroll until end
        # =====================================

        print("Scrolling...")

        last_height = 0

        while True:

            page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            page.wait_for_timeout(1500)

            height = page.evaluate(
                "document.body.scrollHeight"
            )

            if height == last_height:
                break

            last_height = height

        print("Finished scrolling.")

        # =====================================
        # Read links
        # =====================================

        print("Extracting groups...")

        links = page.eval_on_selector_all(
            "a[href*='/groups/']",
            """
            elements => elements.map(el => ({
                text: el.innerText,
                href: el.href
            }))
            """
        )

        print(f"Total links found: {len(links)}")

        saved = 0
        seen = set()

        for item in links:

            url = item.get("href", "").split("?")[0].rstrip("/")

            # -------------------------
            # Ignore navigation links
            # -------------------------

            if url.endswith("/groups"):
                continue

            if "/groups/feed" in url:
                continue

            if "/groups/discover" in url:
                continue

            if "/groups/joins" in url:
                continue

            if "/groups/create" in url:
                continue

            if "/groups/?category" in url:
                continue

            # -------------------------
            # Clean group name
            # -------------------------

            text = item.get("text", "").strip()

            lines = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
            ]

            name = ""

            for line in lines:

                lower = line.lower()

                if lower.startswith("last active"):
                    continue

                if lower.startswith("you last visited"):
                    continue

                if lower.startswith("visited"):
                    continue

                if lower.startswith("unread"):
                    continue

                if lower.startswith("new activity"):
                    continue

                if lower.startswith("new posts"):
                    continue

                if lower.startswith("members"):
                    continue

                if lower.startswith("private group"):
                    continue

                name = line
                break

            if not name:
                continue

            # -------------------------
            # Duplicate?
            # -------------------------

            if url in seen:
                continue

            seen.add(url)

            # -------------------------
            # Save
            # -------------------------

            db.upsert_group(
                account_id=account_id,
                name=name,
                url=url,
                members=""
            )

            saved += 1

            print(f"[{saved}] {name}")

        print("-" * 50)
        print(f"Unique groups saved : {saved}")
        print("-" * 50)

        return {
            "saved": saved,
            "links_found": len(links),
        }


scanner = GroupScanner()
