import time
import threading
import traceback
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class Composer:
    OPEN_TEXTS = [
        "Write something",
        "Create a public post",
        "Create post",
        "What's on your mind",
        "اكتب شيئًا",
        "إنشاء منشور",
        "بم تفكر",
    ]

    def __init__(self):
        self.log_path = Path("logs/composer.log")
        self.last_candidates = []
        self.last_chosen = ""
        self.last_insert_method = ""
        self.last_insert_attempts = []
        self.last_failure_message = ""
        self.last_thread_info = {}
        self.last_exception_type = ""
        self.last_exception_message = ""
        self._log(f"composer_runtime_file={Path(__file__).resolve()}")

    def open(self, page):
        for text in self.OPEN_TEXTS:
            if self._click_text_fallback(page, text):
                dialog = self.visible_dialog(page)

                if dialog:
                    editor = self.editor(dialog)

                    if editor:
                        return dialog, editor

        dialog = self.visible_dialog(page)

        if not dialog:
            return None, None

        return dialog, self.editor(dialog)

    def visible_dialog(self, page):
        try:
            page.locator("div[role='dialog']").first.wait_for(state="visible", timeout=8000)
        except PlaywrightTimeoutError:
            return None

        dialogs = page.locator("div[role='dialog']")

        for index in range(dialogs.count()):
            dialog = dialogs.nth(index)

            try:
                if dialog.is_visible(timeout=1000):
                    return dialog
            except Exception:
                continue

        return None

    def editor(self, dialog):
        locator_groups = [
            ("role_textbox", dialog.get_by_role("textbox")),
            ("contenteditable", dialog.locator("[contenteditable='true']")),
            ("role_contenteditable", dialog.locator("[role='textbox'][contenteditable='true']")),
            ("visible_contenteditable_div", dialog.locator("div[contenteditable='true']:visible")),
        ]
        candidates = []

        for strategy, locator in locator_groups:
            try:
                for index in range(locator.count()):
                    candidate = locator.nth(index)
                    details = self._candidate_details(candidate, strategy, index)
                    candidates.append((candidate, details))
            except Exception:
                continue

        self.last_candidates = [details for _candidate, details in candidates]
        self._log_candidates(self.last_candidates)

        viable = [
            (candidate, details)
            for candidate, details in candidates
            if details["visible"]
            and details["editable"]
            and not details["aria_hidden"]
            and details["has_box"]
        ]

        if not viable:
            self.last_chosen = ""
            return None

        chosen, details = sorted(
            viable,
            key=lambda item: item[1]["area"],
            reverse=True,
        )[0]
        self.last_chosen = details["strategy"]
        self._log(f"chosen={details}")
        return chosen

    def fill_text(self, page, dialog, editor, text, worker_thread_id=None):
        try:
            return self._fill_text(page, dialog, editor, text, worker_thread_id=worker_thread_id)
        except BaseException as error:
            self.last_exception_type = type(error).__name__
            self.last_exception_message = str(error)
            self.last_failure_message = f"composer insertion failed: {type(error).__name__}: {error}"
            self._log_exception("composer_insert:base_exception", error)
            return False

    def _fill_text(self, page, dialog, editor, text, worker_thread_id=None):
        self.last_insert_attempts = []
        self.last_insert_method = ""
        self.last_failure_message = ""
        started = time.monotonic()
        insertion_thread_id = threading.get_ident()
        self.last_thread_info = {
            "browser_worker_thread_id": worker_thread_id,
            "insertion_thread_id": insertion_thread_id,
        }
        self._log(
            " ".join(
                [
                    "composer_insert:start",
                    f"browser_worker_thread_id={worker_thread_id}",
                    f"insertion_thread_id={insertion_thread_id}",
                ]
            )
        )

        if worker_thread_id is not None and insertion_thread_id != worker_thread_id:
            self.last_failure_message = "Composer insertion ran outside BrowserWorker thread"
            self._log(self.last_failure_message)
            return False

        if not text:
            self._log("final_text_length=0")
            self.last_failure_message = "Post content is empty"
            return False

        self._log(f"final_text_length={len(text)}")

        step = "composer_insert:start"

        try:
            dialog, editor = self._ensure_fresh_editor(page, dialog, editor)

            if not dialog or not editor:
                self.last_failure_message = "Composer editor became unavailable before insertion"
                return False

            if self._deadline_exceeded(started):
                self.last_failure_message = "Composer text insertion timed out"
                self._log("composer_insert:timeout")
                return False

            lexical_value = self._get_attribute(editor, "data-lexical-editor")
            before_length = self._current_text_length(editor)

            step = "composer_insert:scroll"
            self._log("composer_insert:scroll_before")
            editor.scroll_into_view_if_needed(timeout=5000)
            self._log("composer_insert:scroll_after")

            step = "composer_insert:click"
            self._log("composer_insert:click_before")
            editor.click(timeout=5000)
            self._log("composer_insert:click_after")

            step = "composer_insert:focus"
            self._log("composer_insert:focus_before")
            editor.focus()
            self._log("composer_insert:focus_after")

            step = "composer_insert:insert"
            self._log("composer_insert:insert_before")
            page.keyboard.insert_text(text)
            self._log("composer_insert:insert_after")

            page.wait_for_timeout(500)

            step = "composer_insert:verify"
            self._log("composer_insert:verify_before")
            after_text = editor.inner_text(timeout=5000)
            after_length = len(self._normalize(after_text))
            verified = self._contains_prefix(after_text, text)
            self._log("composer_insert:verify_after")

            method_name = "keyboard_insert_text"
            self.last_insert_attempts.append(
                {
                    "method": method_name,
                    "before_length": before_length,
                    "after_length": after_length,
                    "verified": verified,
                    "exception_type": "",
                    "exception_message": "",
                    "data_lexical_editor": lexical_value,
                }
            )
            self._log_insertion_attempt(
                page=page,
                editor=editor,
                method_name=method_name,
                before_length=before_length,
                after_length=after_length,
                verified=verified,
                exception_type="",
                lexical_value=lexical_value,
            )

            if verified:
                self.last_insert_method = method_name
                return True

            self.last_failure_message = "Composer content was not inserted"
            return False

        except BaseException as error:
            self.last_exception_type = type(error).__name__
            self.last_exception_message = str(error)
            self.last_failure_message = f"{step} failed: {type(error).__name__}: {error}"
            self._log_exception(step, error)
            return False

    def verify_inserted(self, editor, text):
        normalized = self._normalize(text)
        prefix = normalized[:30]

        if not prefix:
            return False

        values = []

        try:
            values.append(editor.inner_text(timeout=5000))
        except Exception as error:
            self._log_exception("composer_insert:verify_inner_text", error)

        try:
            values.append(editor.text_content(timeout=5000))
        except Exception as error:
            self._log_exception("composer_insert:verify_text_content", error)

        try:
            values.append(editor.get_attribute("data-lexical-editor", timeout=5000) or "")
        except Exception as error:
            self._log_exception("composer_insert:verify_data_lexical", error)

        return any(prefix in self._normalize(value) for value in values)

    def insertion_summary(self, editor):
        try:
            lexical_value = editor.get_attribute("data-lexical-editor") or ""
        except Exception:
            lexical_value = ""

        return {
            "chosen_locator": self.last_chosen,
            "insertion_method": self.last_insert_method,
            "attempts": list(self.last_insert_attempts),
            "after_text_length": self._current_text_length(editor),
            "data_lexical_editor": lexical_value,
            "browser_worker_thread_id": self.last_thread_info.get("browser_worker_thread_id"),
            "insertion_thread_id": self.last_thread_info.get("insertion_thread_id"),
            "failure_message": self.last_failure_message,
        }

    def _keyboard_insert_text(self, page, editor, text):
        editor.click(timeout=5000, force=False)
        page.keyboard.insert_text(text)

    def _press_sequentially(self, editor, text):
        editor.click(timeout=5000, force=False)
        editor.press_sequentially(text, delay=5, timeout=15000)

    def _contains_prefix(self, actual, expected):
        normalized_expected = self._normalize(expected)
        prefix = normalized_expected[:30]

        if not prefix:
            return False

        return prefix in self._normalize(actual)

    def _current_text_length(self, editor):
        values = []

        try:
            values.append(editor.inner_text(timeout=5000))
        except Exception as error:
            self._log_exception("composer_insert:length_inner_text", error)

        try:
            values.append(editor.text_content(timeout=5000))
        except Exception as error:
            self._log_exception("composer_insert:length_text_content", error)

        normalized_values = [self._normalize(value) for value in values if value is not None]
        return max([len(value) for value in normalized_values] or [0])

    def _ensure_fresh_editor(self, page, dialog, editor):
        if self._dialog_and_editor_ready(dialog, editor):
            return dialog, editor

        self._log("composer_insert:reacquire_before")
        dialog = self.visible_dialog(page)

        if not dialog:
            self._log("composer_insert:reacquire_after dialog_found=False")
            return None, None

        editor = self.editor(dialog)
        ready = self._dialog_and_editor_ready(dialog, editor)
        self._log(f"composer_insert:reacquire_after dialog_found=True editor_ready={ready}")
        return (dialog, editor) if ready else (dialog, None)

    def _dialog_and_editor_ready(self, dialog, editor):
        if not dialog or not editor:
            return False

        try:
            return (
                dialog.is_visible(timeout=5000)
                and editor.is_visible(timeout=5000)
                and editor.is_editable(timeout=5000)
            )
        except Exception as error:
            self._log_exception("composer_insert:stale_check", error)
            return False

    def _step(self, name, action):
        before = f"{name}_before"
        after = f"{name}_after"
        self._log(before)

        try:
            action()
            self._log(after)
            return True
        except Exception as error:
            self.last_exception_type = type(error).__name__
            self.last_exception_message = str(error)
            self.last_failure_message = f"{name} failed: {type(error).__name__}: {error}"
            self._log_exception(name, error)
            self._log(after)
            return False

    def _deadline_exceeded(self, started):
        return time.monotonic() - started > 20

    def _get_attribute(self, locator, name):
        try:
            return locator.get_attribute(name, timeout=5000) or ""
        except Exception as error:
            self._log_exception(f"composer_insert:get_attribute:{name}", error)
            return ""

    def _log_insertion_attempt(
        self,
        page,
        editor,
        method_name,
        before_length,
        after_length,
        verified,
        exception_type,
        lexical_value,
    ):
        active = self._active_element_details(page)
        self._log(
            " ".join(
                [
                    f"insertion_method={method_name}",
                    f"before_length={before_length}",
                    f"after_length={after_length}",
                    f"verified={verified}",
                    f"exception_type={exception_type}",
                    f"data_lexical_editor={lexical_value}",
                    f"active_element_tag={active['tag']}",
                    f"active_element_role={active['role']}",
                ]
            )
        )

    def _active_element_details(self, page):
        try:
            return page.evaluate(
                """
                () => ({
                    tag: document.activeElement ? document.activeElement.tagName : '',
                    role: document.activeElement ? (document.activeElement.getAttribute('role') || '') : ''
                })
                """
            )
        except Exception:
            return {
                "tag": "",
                "role": "",
            }

    def _log_exception(self, step, error):
        self._log(
            " ".join(
                [
                    f"step={step}",
                    f"exception_type={type(error).__name__}",
                    f"exception_message={error}",
                    f"traceback={traceback.format_exc()}",
                ]
            )
        )

    def _candidate_details(self, locator, strategy, index):
        details = {
            "strategy": strategy,
            "index": index,
            "tag": "",
            "role": "",
            "aria_label": "",
            "contenteditable": "",
            "visible": False,
            "editable": False,
            "aria_hidden": False,
            "has_box": False,
            "area": 0,
        }

        try:
            attrs = locator.evaluate(
                """
                element => ({
                    tag: element.tagName,
                    role: element.getAttribute('role') || '',
                    ariaLabel: element.getAttribute('aria-label') || '',
                    contenteditable: element.getAttribute('contenteditable') || '',
                    ariaHidden: element.getAttribute('aria-hidden') === 'true'
                })
                """
            )
            details.update(
                {
                    "tag": attrs.get("tag", ""),
                    "role": attrs.get("role", ""),
                    "aria_label": attrs.get("ariaLabel", ""),
                    "contenteditable": attrs.get("contenteditable", ""),
                    "aria_hidden": bool(attrs.get("ariaHidden")),
                }
            )
        except Exception:
            pass

        try:
            details["visible"] = locator.is_visible(timeout=500)
        except Exception:
            pass

        try:
            details["editable"] = locator.is_editable(timeout=500)
        except Exception:
            pass

        try:
            box = locator.bounding_box(timeout=500)
            details["has_box"] = bool(box and box.get("width") and box.get("height"))
            details["area"] = int((box.get("width") or 0) * (box.get("height") or 0)) if box else 0
        except Exception:
            pass

        return details

    def _click_text_fallback(self, page, text):
        locators = [
            page.get_by_role("button", name=text).first,
            page.get_by_text(text, exact=False).first,
        ]

        for locator in locators:
            try:
                if locator.count() > 0 and locator.is_visible(timeout=1000):
                    locator.click(timeout=3000)
                    return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue

        return False

    def _log_candidates(self, candidates):
        for candidate in candidates:
            self._log(f"candidate={candidate}")

    def _log(self, message):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        text = str(message)

        if "encrypted_context" in text:
            text = "[redacted encrypted context]"

        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text[:2000]}\n")

    def _normalize(self, value):
        return " ".join(str(value or "").split())
