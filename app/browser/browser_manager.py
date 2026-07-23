from app.browser.browser_worker import BrowserWorker
from threading import Event


class BrowserManager:
    """Thread-safe facade for the dedicated BrowserWorker."""

    def __init__(self):
        self.worker = BrowserWorker()
        self.publish_stop_event = Event()

    def start_account(self, account):
        return self.worker.execute(
            "account switch",
            lambda: self.worker.switch_account(account),
        )

    def start_for_account(self, account):
        return self.start_account(account)

    def switch_account(self, account):
        self.publish_stop_event.set()
        return self.start_account(account)

    def goto(self, url):
        def handler():
            page = self.worker.require_page()
            page.goto(url, wait_until="domcontentloaded")
            return self._result(True, "navigating", f"Navigated to {url}", {"url": page.url})

        return self.worker.execute("navigating", handler)

    def scan_groups(self, account_id=None):
        def handler():
            page = self.worker.require_page()
            from app.services.group_scanner import scanner

            data = scanner.scan_page(page, account_id=account_id)
            return self._result(True, "scanning groups", "Groups scan finished", data)

        return self.worker.execute("scanning groups", handler)

    def analyze_groups(self, account_id=None):
        def handler():
            page = self.worker.require_page()
            from app.services.group_analyzer import analyzer

            data = analyzer.analyze_page(page, account_id=account_id)
            return self._result(True, "analyzing groups", "Groups analysis finished", data)

        return self.worker.execute("analyzing groups", handler)

    def check_login(self):
        def handler():
            page = self.worker.require_page()
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

    def publish(self, request, account, post, groups, progress=None, history=None, rate_limit=None):
        self.publish_stop_event.clear()

        def handler():
            self.worker.set_publishing_active(True)
            self.worker._log("publish_run_started", f"account_id={request.account_id}")
            page = self.worker.ensure_page_for_account(account)
            required_generation = self.worker.current_generation()
            from app.publisher.engine import PublisherEngine

            try:
                engine = PublisherEngine(
                    page_recovery=lambda: self.worker.recover_page(required_generation=required_generation),
                    current_account_id=lambda: self.worker.get_state().get("account_id"),
                    page_generation=lambda: self.worker.current_generation(),
                    on_rate_limited=rate_limit,
                )
                data = engine.run(
                    page=page,
                    request=request,
                    post=post,
                    groups=groups,
                    stop_event=self.publish_stop_event,
                    progress=progress,
                    history=history,
                    worker_thread_id=self.worker.get_state().get("owner_thread_id"),
                )
                return self._result(True, "publishing", "Publishing run finished", data)
            finally:
                self.worker._log("publish_run_finished", "")
                self.worker.set_publishing_active(False)

        return self.worker.execute("publishing", handler)

    def stop_publish(self):
        self.publish_stop_event.set()
        return self._result(True, "publishing", "Stop requested")

    def close(self, source="unknown"):
        return self.shutdown()

    def stop(self, source="stop"):
        return self.close(source=source)

    def shutdown(self):
        return self.worker.shutdown()

    def is_running(self):
        return bool(self.worker.get_state().get("running"))

    def is_publishing(self):
        state = self.worker.get_state()
        return bool(state.get("publishing_active") or state.get("operation") == "publishing")

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
