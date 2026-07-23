from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class GroupNavigator:
    LOGIN_SELECTORS = [
        "input[name='email']",
        "input[name='pass']",
    ]
    UNAVAILABLE_TEXT = [
        "This content isn't available",
        "This group isn't available",
        "هذا المحتوى غير متاح",
        "هذه المجموعة غير متاحة",
    ]
    PERMISSION_TEXT = [
        "You can't post",
        "Only admins can post",
        "Only admins and moderators can post",
        "Your request to join is pending",
        "Cancel request",
        "لا يمكنك النشر",
        "المسؤولون فقط",
        "طلب الانضمام معلق",
    ]
    BLOCK_TEXT = [
        "You're temporarily blocked",
        "We limit how often",
        "You can't use this feature right now",
        "تم حظرك مؤقتًا",
        "نحد من عدد المرات",
    ]
    CHECKPOINT_TEXT = [
        "security check",
        "confirm your identity",
        "two-factor authentication",
        "فحص أمان",
        "تأكيد هويتك",
    ]

    def open_group(self, page, group, on_attempt=None):
        timed_out = False

        for attempt in (1, 2):
            if on_attempt:
                on_attempt(attempt)

            try:
                if attempt == 1:
                    page.goto(group["url"], wait_until="domcontentloaded", timeout=45000)
                else:
                    if self.belongs_to_group(page.url, group["url"]):
                        page.reload(wait_until="domcontentloaded", timeout=45000)
                    else:
                        page.goto(group["url"], wait_until="domcontentloaded", timeout=45000)
            except PlaywrightTimeoutError:
                timed_out = True
                state, message = self._usable_partial_page(page, group)

                if state:
                    return state, message

                if attempt == 1:
                    continue

                return "Failed", "Group page could not be loaded after one retry"

            try:
                page.locator("body").wait_for(state="visible", timeout=10000)
            except PlaywrightTimeoutError:
                if attempt == 1:
                    continue
                return "Failed", "Group page could not be loaded after one retry"

            page.wait_for_timeout(1500)
            state, message = self.detect_page_state(page)

            if state != "Ready":
                return state, message

            if self.belongs_to_group(page.url, group["url"]):
                return "Ready", "Group opened."

            if attempt == 2:
                return "Failed", "Group page could not be loaded after one retry"

        if timed_out:
            return "Failed", "Group page could not be loaded after one retry"

        return "Failed", "Group page could not be loaded after one retry"

    def detect_page_state(self, page):
        url = page.url.lower()

        if "two_step_verification" in url:
            return "TwoFactor", "Two-factor authentication is required."

        if "checkpoint" in url:
            return "Checkpoint", "Facebook checkpoint is required."

        if "login" in url or self._has_login_form(page):
            return "LoginRequired", "Facebook login is required."

        body = self._body_text(page)
        body_lower = body.lower()

        if any(text.lower() in body_lower for text in self.CHECKPOINT_TEXT):
            return "Checkpoint", "Facebook security checkpoint is required."

        if any(text.lower() in body_lower for text in self.BLOCK_TEXT):
            return "Blocked", "Facebook temporarily restricted publishing."

        if any(text.lower() in body_lower for text in self.UNAVAILABLE_TEXT):
            return "Unavailable", "Group is unavailable."

        if any(text.lower() in body_lower for text in self.PERMISSION_TEXT):
            return "PermissionDenied", "Posting permission appears unavailable."

        return "Ready", "Group opened."

    def belongs_to_group(self, current_url, intended_url):
        current = self._group_key(current_url)
        intended = self._group_key(intended_url)
        return bool(current and intended and current == intended)

    def _usable_partial_page(self, page, group):
        try:
            if page.is_closed():
                return None, ""

            state, message = self.detect_page_state(page)

            if state != "Ready":
                return state, message

            body_visible = page.locator("body").is_visible(timeout=2000)

            if body_visible and self.belongs_to_group(page.url, group["url"]):
                return "Ready", "Group page partially loaded but is usable."
        except Exception:
            pass

        return None, ""

    def _group_key(self, url):
        try:
            parts = [part for part in urlparse(url).path.split("/") if part]
            index = parts.index("groups")
            return parts[index + 1].lower()
        except (ValueError, IndexError):
            return ""

    def _has_login_form(self, page):
        for selector in self.LOGIN_SELECTORS:
            try:
                if page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue

        return False

    def _body_text(self, page):
        try:
            return page.locator("body").inner_text(timeout=5000)
        except PlaywrightTimeoutError:
            return ""
