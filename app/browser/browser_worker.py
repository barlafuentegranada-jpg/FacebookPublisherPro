import locale
import os
import queue
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class InvalidEnvironment(RuntimeError):
    pass


@dataclass
class Environment:
    browser: object = None
    context: object = None
    page: object = None
    account_id: int = None
    account_name: str = ""
    profile_path: str = ""
    playwright: object = None
    worker_thread_id: int = None
    generation_id: int = 0


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
        self.environment = None
        self.generation_id = 0
        self.state = {
            "running": False,
            "profile_path": "",
            "account_id": None,
            "account_name": None,
            "generation_id": 0,
            "busy": False,
            "operation": "",
            "owner_thread_id": None,
            "publishing_active": False,
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
            if self.state.get("publishing_active") and operation != "publishing":
                if operation == "close":
                    self._log(
                        "browser_close_blocked",
                        "publishing_active=True",
                    )
                return self._result(
                    False,
                    operation,
                    "Publishing is running. Stop it before switching accounts or restarting the browser.",
                )

            if self.busy_operation:
                if self.busy_operation == "publishing":
                    if operation == "close":
                        self._log(
                            "browser_close_blocked",
                            "publishing_active=True",
                        )
                    return self._result(
                        False,
                        operation,
                        "Publishing is running. Stop it before switching accounts or restarting the browser.",
                    )

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
        owner_thread_id = threading.get_ident()
        self._set_state(owner_thread_id=owner_thread_id)
        self.environment = None
        self.started.set()

        while True:
            operation, handler, result_queue = self.queue.get()

            if operation == "shutdown":
                self._dispose_environment(source="shutdown")
                self._set_state(running=False, account_id=None, account_name=None, profile_path="", generation_id=self.generation_id)
                result_queue.put(self._result(True, operation, "Browser shutdown complete"))
                self._clear_busy()
                break

            try:
                result = handler()
                result_queue.put(result)
            except (PlaywrightError, PlaywrightTimeoutError) as error:
                self._log_traceback(operation)
                result_queue.put(self._result(False, operation, str(error)))
            except Exception as error:
                self._log_traceback(operation)
                result_queue.put(self._result(False, operation, str(error)))
            finally:
                self._clear_busy()

    def switch_account(self, account):
        target_profile = str(Path(account["profile_path"]).resolve())

        if (
            self.environment
            and self._context_alive(self.environment.context)
            and self.state.get("profile_path") == target_profile
            and self.state.get("account_id") == account["id"]
        ):
            return self._result(True, "account switch", "Account already running", self.get_state())

        self._dispose_environment(source="switch_account")

        playwright = sync_playwright().start()
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
            context = playwright.chromium.launch_persistent_context(
                channel="chrome",
                **launch_options,
            )
        except Exception as error:
            self._log("chrome_launch_failed", str(error))
            context = playwright.chromium.launch_persistent_context(
                **launch_options,
            )

        page = context.new_page()
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=0)
        self.generation_id += 1
        self._log("browser_generation", f"generation={self.generation_id}")
        self._attach_diagnostics(context, page)

        self.environment = Environment(
            browser=getattr(context, "browser", None),
            context=context,
            page=page,
            account_id=account["id"],
            account_name=account["name"],
            profile_path=target_profile,
            playwright=playwright,
            worker_thread_id=threading.get_ident(),
            generation_id=self.generation_id,
        )
        self._set_state(
            running=True,
            profile_path=target_profile,
            account_id=account["id"],
            account_name=account["name"],
            generation_id=self.generation_id,
        )
        return self._result(True, "account switch", "Account browser started", self.get_state())

    def ensure_page_for_account(self, account, required_generation=None):
        if not self.environment or self.environment.account_id != account["id"]:
            result = self.switch_account(account)

            if not result.get("success"):
                raise RuntimeError(result.get("message") or "Could not switch account browser.")

            required_generation = self.generation_id

        return self.require_page(required_generation=required_generation)

    def require_page(self, required_generation=None):
        environment = self.environment
        current_generation = self.generation_id
        required = current_generation if required_generation is None else required_generation
        self._log("require_page", f"required_generation={required} current_generation={current_generation}")

        if required != current_generation:
            raise InvalidEnvironment(
                f"Browser environment generation changed: required={required} current={current_generation}"
            )

        if environment is None or environment.context is None:
            raise InvalidEnvironment("Browser environment is not available.")

        if not self._context_alive(environment.context):
            raise InvalidEnvironment("Browser context is not available.")

        page = environment.page

        if page is None or page.is_closed():
            raise InvalidEnvironment("Browser page is not available.")

        self._log("ensure_page", "page_alive=True page_recreated=False")
        return page

    def recover_page(self, required_generation=None):
        environment = self.environment
        current_generation = self.generation_id
        required = current_generation if required_generation is None else required_generation
        self._log("recover_page", f"required_generation={required} current_generation={current_generation}")

        if required != current_generation:
            raise InvalidEnvironment(
                f"Browser environment generation changed: required={required} current={current_generation}"
            )

        if environment is None or environment.context is None:
            raise InvalidEnvironment("Browser environment is not available.")

        if not self._context_alive(environment.context):
            raise InvalidEnvironment("Browser context is not available.")

        page = environment.page

        if page is None or page.is_closed():
            page = environment.context.new_page()
            environment.page = page
            self._attach_page_diagnostics(page)
            self._log("ensure_page", "page_alive=True page_recreated=True")
            return page

        self._log("ensure_page", "page_alive=True page_recreated=False")
        return page

    def current_generation(self):
        return self.generation_id

    def set_publishing_active(self, active):
        self._set_state(publishing_active=active)

    def _context_alive(self, context):
        if context is None:
            return False

        try:
            context.pages
            return True
        except Exception:
            return False

    def _dispose_environment(self, source="unknown"):
        if source not in {"shutdown", "switch_account"}:
            raise RuntimeError(f"Environment disposal is not allowed from {source}.")

        environment = self.environment
        self.environment = None
        self._set_state(running=False, account_id=None, account_name=None, profile_path="", generation_id=self.generation_id)
        self._log("browser_close_requested", f"source={source}")

        if environment:
            if environment.page:
                environment.page = None

            context = environment.context
            environment.context = None
            environment.browser = None

            if context:
                try:
                    context.close()
                except Exception:
                    self._log_traceback("dispose_context")

            if environment.playwright:
                try:
                    environment.playwright.stop()
                except Exception:
                    self._log_traceback("stop_playwright")
                environment.playwright = None

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
