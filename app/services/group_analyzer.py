from playwright.sync_api import TimeoutError

from app.database.db import db


class GroupAnalyzer:

    def analyze(self):
        from app.browser.browser_manager import browser

        return browser.analyze_groups()

    def analyze_page(self, page, account_id=None):

        groups = db.get_groups(account_id=account_id)

        print(f"Analyzing {len(groups)} groups...")

        analyzed = 0
        failed = 0

        for group in groups:

            url = group["url"]

            print("-" * 60)
            print(url)

            try:

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                page.wait_for_timeout(2500)

                title = ""

                try:
                    title = page.locator("h1").first.inner_text(timeout=3000)
                except:
                    pass

                members = ""

                try:
                    text = page.locator("body").inner_text()

                    for line in text.splitlines():

                        low = line.lower()

                        if (
                            "members" in low
                            or "member" in low
                            or "عضو" in line
                            or "أعضاء" in line
                        ):
                            members = line.strip()
                            break

                except:
                    pass

                privacy = ""

                if "Private group" in page.content():
                    privacy = "Private"

                elif "Public group" in page.content():
                    privacy = "Public"

                db.update_group_info(
                    group["id"],
                    title if title else group["name"],
                    members,
                    privacy
                )

                print(title)
                print(members)
                print(privacy)
                analyzed += 1

            except TimeoutError:

                print("Timeout")
                failed += 1

            except Exception as e:

                print(e)
                failed += 1

        return {
            "analyzed": analyzed,
            "failed": failed,
        }


analyzer = GroupAnalyzer()
