import locale
import os
import queue
import threading
import time
import traceback
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class BrowserWorker:
    """Single-thread owner for all Playwright objects."""

    BUSY_OPERATIONS = {
        "account switch",
        "analyzing groups",
        "checking login",
        "navigating",
        "publishing",
        "scanning groups",
    }

    def __init__(self):
        self.queue = queue.Queue()
        self.thread = None
        self.started = threading.Event()
        self.lock = threading.Lock()
        self.busy_operation = None
        self.state = {
            "running": False,
            "profile_path": "",
            "account_id": None,
            "account_name": None,
            "busy": False,
            "operation": "",
        }
        self.log_path = Path("logs/browser.log")

    def start_thread(self):
        if self.thread and self.thread.is_alive():
            return

        self.started.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name="BrowserWorker")
        self.thread.start()
        self.started.wait(timeout=10)

    def execute(self, operation, handler, wait=True):
        self.start_thread()

        with self.lock:
            if self.busy_operation:
                return self._result(
                    False,
                    operation,
                    f"Browser is busy: {self.busy_operation}",
                )
            self.busy_operation = operation
            self.state["busy"] = True
            self.state["operation"] = operation

        result_queue = queue.Queue(maxsize=1)
        self.queue.put((operation, handler, result_queue))

        if not wait:
            return self._result(True, operation, "Queued")

        return result_queue.get()

    def shutdown(self):
        if not self.thread or not self.thread.is_alive():
            return self._result(True, "shutdown", "Browser worker already stopped")

        result_queue = queue.Queue(maxsize=1)
        self.queue.put(("shutdown", None, result_queue))
        result = result_queue.get(timeout=30)
        self.thread.join(timeout=30)
        return result

    def get_state(self):
        with self.lock:
            return self.state.copy()

    def _run(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        playwright = None
        context = None
        page = None
        self.started.set()

        while True:
            operation, handler, result_queue = self.queue.get()

            if operation == "shutdown":
                context, page = self._close_context(context)
                if playwright:
                    try:
                        playwright.stop()
                    except Exception:
                        self._log_traceback("shutdown_stop_playwright")
                playwright = None
                self._set_state(running=False, account_id=None, account_name=None, profile_path="")
                result_queue.put(self._result(True, operation, "Browser shutdown complete"))
                self._clear_busy()
                break

            try:
                environment = {
                    "playwright": playwright,
                    "context": context,
                    "page": page,
                }
                result = handler(environment)
                playwright = environment.get("playwright")
                context = environment.get("context")
                page = environment.get("page")
                result_queue.put(result)
            except (PlaywrightError, PlaywrightTimeoutError) as error:
                self._log_traceback(operation)
                result_queue.put(self._result(False, operation, str(error)))
            except Exception as error:
                self._log_traceback(operation)
                result_queue.put(self._result(False, operation, str(error)))
            finally:
                self._clear_busy()

    def start_account_context(self, environment, account):
        target_profile = str(Path(account["profile_path"]).resolve())

        if (
            environment.get("context")
            and self.state.get("profile_path") == target_profile
            and self.state.get("account_id") == account["id"]
        ):
            return self._result(True, "account switch", "Account already running", self.get_state())

        environment["context"], environment["page"] = self._close_context(environment.get("context"))
        self._set_state(running=False, account_id=None, account_name=None, profile_path="")

        if environment.get("playwright"):
            try:
                environment["playwright"].stop()
            except Exception:
                self._log_traceback("stop_playwright_before_switch")
            environment["playwright"] = None

        environment["playwright"] = sync_playwright().start()
        Path(target_profile).mkdir(parents=True, exist_ok=True)

        launch_options = {
            "user_data_dir": target_profile,
            "headless": False,
            "no_viewport": True,
            "locale": self._system_locale(),
            "timezone_id": self._system_timezone_id(),
            "accept_downloads": True,
        }

        try:
            environment["context"] = environment["playwright"].chromium.launch_persistent_context(
                channel="chrome",
                **launch_options,
            )
        except Exception as error:
            self._log("chrome_launch_failed", str(error))
            environment["context"] = environment["playwright"].chromium.launch_persistent_context(
                **launch_options,
            )

        pages = environment["context"].pages
        environment["page"] = pages[0] if pages else environment["context"].new_page()
        self._attach_diagnostics(environment["context"], environment["page"])
        self._set_state(
            running=True,
            profile_path=target_profile,
            account_id=account["id"],
            account_name=account["name"],
        )
        return self._result(True, "account switch", "Account browser started", self.get_state())

    def close_context(self, environment):
        environment["context"], environment["page"] = self._close_context(environment.get("context"))

        if environment.get("playwright"):
            environment["playwright"].stop()
            environment["playwright"] = None

        self._set_state(running=False, account_id=None, account_name=None, profile_path="")
        return self._result(True, "close", "Browser closed", self.get_state())

    def require_page(self, environment):
        page = environment.get("page")

        if page is None:
            raise RuntimeError("Browser is not running.")

        return page

    def _close_context(self, context):
        if context:
            try:
                context.close()
            except Exception:
                self._log_traceback("close_context")

        return None, None

    def _attach_diagnostics(self, context, page):
        self._attach_page_diagnostics(page)
        context.on("page", self._attach_page_diagnostics)

    def _attach_page_diagnostics(self, page):
        page.on("console", lambda message: self._log("console", f"{message.type}: {message.text}"))
        page.on("pageerror", lambda error: self._log("pageerror", str(error)))
        page.on(
            "requestfailed",
            lambda request: self._log(
                "requestfailed",
                f"{request.method} {self._sanitize_url(request.url)} {request.failure}",
            ),
        )

    def _set_state(self, **updates):
        with self.lock:
            self.state.update(updates)

    def _clear_busy(self):
        with self.lock:
            self.busy_operation = None
            self.state["busy"] = False
            self.state["operation"] = ""

    def _result(self, success, operation, message, data=None):
        return {
            "success": success,
            "operation": operation,
            "message": message,
            "data": data,
        }

    def _log_traceback(self, operation):
        self._log(operation, traceback.format_exc())

    def _log(self, event, message):
        safe_message = self._sanitize_text(message)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {event}: {safe_message}\n")

    def _sanitize_text(self, value):
        text = str(value)

        if "encrypted_context" in text:
            return "[redacted encrypted context]"

        return text.replace("\n", " ")[:4000]

    def _sanitize_url(self, url):
        if "encrypted_context" in url:
            return "[redacted encrypted context url]"

        return url.split("?")[0]

    def _system_locale(self):
        language, _encoding = locale.getdefaultlocale()

        if not language:
            return "en-US"

        return language.replace("_", "-")

    def _system_timezone_id(self):
        return os.environ.get("TZ") or "Europe/Istanbul"
