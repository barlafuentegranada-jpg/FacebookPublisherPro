from app.browser.browser_worker import BrowserWorker


class BrowserManager:
    """Thread-safe facade for the dedicated BrowserWorker."""

    def __init__(self):
        self.worker = BrowserWorker()

    def start_account(self, account):
        return self.worker.execute(
            "account switch",
            lambda environment: self.worker.start_account_context(environment, account),
        )

    def start_for_account(self, account):
        return self.start_account(account)

    def switch_account(self, account):
        return self.start_account(account)

    def goto(self, url):
        def handler(environment):
            page = self.worker.require_page(environment)
            page.goto(url, wait_until="domcontentloaded")
            return self._result(True, "navigating", f"Navigated to {url}", {"url": page.url})

        return self.worker.execute("navigating", handler)

    def scan_groups(self, account_id=None):
        def handler(environment):
            page = self.worker.require_page(environment)
            from app.services.group_scanner import scanner

            data = scanner.scan_page(page, account_id=account_id)
            return self._result(True, "scanning groups", "Groups scan finished", data)

        return self.worker.execute("scanning groups", handler)

    def analyze_groups(self, account_id=None):
        def handler(environment):
            page = self.worker.require_page(environment)
            from app.services.group_analyzer import analyzer

            data = analyzer.analyze_page(page, account_id=account_id)
            return self._result(True, "analyzing groups", "Groups analysis finished", data)

        return self.worker.execute("analyzing groups", handler)

    def check_login(self):
        def handler(environment):
            page = self.worker.require_page(environment)
            page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=0)
            page.wait_for_timeout(1500)

            url = self.worker._sanitize_url(page.url)
            has_login_form = (
                page.locator("input[name='email']").count() > 0
                or page.locator("input[name='pass']").count() > 0
            )
            body = page.locator("body").inner_text(timeout=7000)
            body_lower = body.lower()
            return self._result(
                True,
                "checking login",
                "Login status checked",
                {
                    "url": url,
                    "has_login_form": has_login_form,
                    "has_two_factor": "two_step_verification" in page.url.lower()
                    or "two-factor" in body_lower
                    or "two factor" in body_lower,
                    "has_checkpoint": "checkpoint" in page.url.lower()
                    or "checkpoint" in body_lower,
                    "has_logged_out_marker": "login" in page.url.lower()
                    or any(
                        marker in body_lower
                        for marker in [
                            "log in",
                            "forgot password",
                            "create new account",
                            "facebook helps you connect",
                            "password",
                        ]
                    ),
                    "has_logged_in_marker": "facebook.com" in page.url.lower()
                    and any(
                        marker in body_lower
                        for marker in [
                            "what's on your mind",
                            "news feed",
                            "marketplace",
                            "groups",
                            "messenger",
                        ]
                    ),
                },
            )

        return self.worker.execute("checking login", handler)

    def close(self):
        return self.worker.execute(
            "close",
            lambda environment: self.worker.close_context(environment),
        )

    def stop(self):
        return self.close()

    def shutdown(self):
        return self.worker.shutdown()

    def is_running(self):
        return bool(self.worker.get_state().get("running"))

    def get_state(self):
        return self.worker.get_state()

    def _result(self, success, operation, message, data=None):
        return {
            "success": success,
            "operation": operation,
            "message": message,
            "data": data,
        }


browser = BrowserManager()
