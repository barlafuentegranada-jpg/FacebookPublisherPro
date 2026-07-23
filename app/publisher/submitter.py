import time
from pathlib import Path


class Submitter:
    BUTTON_TEXTS = ["Post", "Publish", "نشر"]
    REJECT_TEXTS = [
        "Add to your post",
        "Cancel",
        "Close",
        "Schedule",
        "Privacy",
        "Audience",
        "إلغاء",
        "إغلاق",
        "جدولة",
    ]

    def __init__(self):
        self.log_path = Path("logs/submitter.log")
        self.last_candidates = []
        self.last_chosen = {}
        self.click_count = 0
        self.last_button = None

    def submit(self, dialog, has_payload, upload_complete=True, content_still_present=True):
        self._log(f"submitter_runtime_file={Path(__file__).resolve()}")
        self._log("submitter:start")

        if not has_payload:
            return False, "Nothing to publish.", {}

        if not content_still_present:
            return False, "Composer content disappeared before submit.", {}

        if not upload_complete:
            return False, "Media upload is not complete.", {}

        dialog.page.wait_for_timeout(1000)
        button = self.wait_for_enabled_button(dialog, timeout_ms=10000)

        if not button:
            return False, "Facebook submit button remained disabled", self.last_chosen

        try:
            if not button.is_visible(timeout=1000) or not button.is_enabled(timeout=1000):
                return False, "Publish button is not ready.", self.last_chosen
        except Exception:
            return False, "Publish button state could not be confirmed.", self.last_chosen

        self.click_count += 1
        self.last_button = button
        self._log("submitter:click_before")
        button.click(timeout=10000)
        self._log("submitter:click_after")
        return True, "Publish clicked.", self.last_chosen

    def wait_for_enabled_button(self, dialog, timeout_ms=10000):
        deadline = time.time() + (timeout_ms / 1000)
        best = None

        while time.time() < deadline:
            candidates = self._collect_candidates(dialog)
            self.last_candidates = [details for _locator, details in candidates]
            self._log_candidates(self.last_candidates)
            valid = [
                (locator, details)
                for locator, details in candidates
                if self._is_valid(details)
            ]

            if valid:
                best, details = sorted(
                    valid,
                    key=lambda item: (item[1]["y"], item[1]["area"]),
                    reverse=True,
                )[0]
                self.last_chosen = details
                self._log(f"chosen={details}")
                return best

            try:
                dialog.page.wait_for_timeout(500)
            except Exception:
                break

        self.last_chosen = {}
        return None

    def _collect_candidates(self, dialog):
        strategies = [
            ("role_post_exact", lambda: dialog.get_by_role("button", name="Post", exact=True)),
            ("role_publish_exact", lambda: dialog.get_by_role("button", name="Publish", exact=True)),
            ("role_arabic_post_exact", lambda: dialog.get_by_role("button", name="نشر", exact=True)),
            ("role_button_text_post", lambda: dialog.locator("[role='button']").filter(has_text="Post")),
            ("role_button_text_publish", lambda: dialog.locator("[role='button']").filter(has_text="Publish")),
            ("role_button_text_arabic", lambda: dialog.locator("[role='button']").filter(has_text="نشر")),
        ]
        candidates = []

        for strategy, factory in strategies:
            try:
                locator = factory()

                for index in range(locator.count()):
                    candidate = locator.nth(index)
                    candidates.append((candidate, self._details(candidate, strategy, index)))
            except Exception:
                continue

        return candidates

    def _details(self, locator, strategy, index):
        details = {
            "strategy": strategy,
            "index": index,
            "tag": "",
            "role": "",
            "inner_text": "",
            "aria_label": "",
            "visible": False,
            "enabled": False,
            "disabled": False,
            "aria_disabled": "",
            "has_box": False,
            "box": "",
            "area": 0,
            "y": 0,
        }

        try:
            attrs = locator.evaluate(
                """
                element => ({
                    tag: element.tagName,
                    role: element.getAttribute('role') || '',
                    innerText: element.innerText || '',
                    ariaLabel: element.getAttribute('aria-label') || '',
                    disabled: element.hasAttribute('disabled'),
                    ariaDisabled: element.getAttribute('aria-disabled') || ''
                })
                """
            )
            details.update(
                {
                    "tag": attrs.get("tag", ""),
                    "role": attrs.get("role", ""),
                    "inner_text": " ".join(str(attrs.get("innerText", "")).split())[:80],
                    "aria_label": str(attrs.get("ariaLabel", ""))[:80],
                    "disabled": bool(attrs.get("disabled")),
                    "aria_disabled": attrs.get("ariaDisabled", ""),
                }
            )
        except Exception:
            pass

        try:
            details["visible"] = locator.is_visible(timeout=500)
        except Exception:
            pass

        try:
            details["enabled"] = locator.is_enabled(timeout=500)
        except Exception:
            pass

        try:
            box = locator.bounding_box(timeout=500)

            if box:
                details["has_box"] = bool(box.get("width") and box.get("height"))
                details["area"] = int((box.get("width") or 0) * (box.get("height") or 0))
                details["y"] = int(box.get("y") or 0)
                details["box"] = {
                    "x": int(box.get("x") or 0),
                    "y": int(box.get("y") or 0),
                    "width": int(box.get("width") or 0),
                    "height": int(box.get("height") or 0),
                }
        except Exception:
            pass

        return details

    def _is_valid(self, details):
        text = f"{details.get('inner_text', '')} {details.get('aria_label', '')}"

        return (
            details["visible"]
            and details["enabled"]
            and details["has_box"]
            and not details["disabled"]
            and str(details["aria_disabled"]).lower() != "true"
            and any(label in text for label in self.BUTTON_TEXTS)
            and not any(label in text for label in self.REJECT_TEXTS)
        )

    def _log_candidates(self, candidates):
        for candidate in candidates:
            self._log(f"candidate={candidate}")

    def _log(self, message):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        text = str(message)

        if "encrypted_context" in text:
            text = "[redacted encrypted context]"

        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text[:3000]}\n")
