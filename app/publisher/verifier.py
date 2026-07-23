import time


class Verifier:
    SUCCESS_TEXTS = [
        "Your post was published",
        "Your post has been published",
        "تم نشر منشورك",
        "تم النشر",
    ]

    def verify(self, page, dialog, final_text, submit_button=None):
        signals = []
        dialog_closed = False
        deadline = time.time() + 30

        while time.time() < deadline:
            dialog_closed = self._dialog_closed(dialog)

            if dialog_closed:
                self._add_signal(signals, "dialog closed")

                if self._success_notification(page):
                    self._add_signal(signals, "success toast")

                if final_text and self._matching_content_visible(page, final_text):
                    self._add_signal(signals, "matching content in feed")

                if self._post_permalink_visible(page):
                    self._add_signal(signals, "post permalink visible")

                if submit_button and self._submit_button_disappeared(submit_button):
                    self._add_signal(signals, "submit button disappeared")

                if len(signals) >= 2:
                    return True, f"Verified by: {', '.join(signals)}.", self._current_url(page), signals

            page.wait_for_timeout(1000)

        if not dialog_closed:
            return False, "Composer remained open after submit click", "", signals

        return False, "Submission completed but publication could not be verified", "", signals

    def _dialog_closed(self, dialog):
        try:
            return not dialog.is_visible(timeout=500)
        except Exception:
            return True

    def _success_notification(self, page):
        for text in self.SUCCESS_TEXTS:
            try:
                if page.get_by_text(text, exact=False).count() > 0:
                    return True
            except Exception:
                continue

        return False

    def _matching_content_visible(self, page, final_text):
        prefix = self._normalize(final_text)[:30]

        if not prefix:
            return False

        try:
            return page.locator("[role='article']").filter(has_text=prefix).first.is_visible(timeout=1000)
        except Exception:
            pass

        try:
            return page.get_by_text(prefix, exact=False).first.is_visible(timeout=1000)
        except Exception:
            return False

    def _post_permalink_visible(self, page):
        selectors = [
            "a[href*='/posts/']",
            "a[href*='story_fbid']",
            "a[href*='/permalink/']",
        ]

        for selector in selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    return True
            except Exception:
                continue

        return False

    def _submit_button_disappeared(self, submit_button):
        try:
            return not submit_button.is_visible(timeout=500)
        except Exception:
            return True

    def _add_signal(self, signals, signal):
        if signal not in signals:
            signals.append(signal)

    def _current_url(self, page):
        url = page.url

        if "encrypted_context" in url:
            return ""

        return url.split("?")[0]

    def _normalize(self, value):
        return " ".join(str(value or "").split())
