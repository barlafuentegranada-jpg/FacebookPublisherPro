class FacebookRateLimitDetector:
    PHRASES = {
        "limit_post_frequency": [
            "We limit how often you can post",
            "نضع قيودًا على عدد مرات",
        ],
        "try_again_later": [
            "You can try again later",
            "يمكنك المحاولة مرة أخرى لاحقًا",
        ],
        "community_spam_protection": [
            "help protect the community from spam",
            "حماية المجتمع من المحتوى غير المرغوب فيه",
        ],
        "temporarily_blocked": [
            "temporarily blocked",
            "تم تقييدك مؤقتًا",
        ],
        "posting_restricted": [
            "restricted from posting",
            "لا يمكنك النشر حاليًا",
        ],
    }

    def detect(self, page, dialog=None, stage=None):
        scopes = [dialog, page] if dialog is not None else [page]

        for key, phrases in self.PHRASES.items():
            for phrase in phrases:
                if self._visible_in_scopes(scopes, phrase):
                    return {
                        "matched_key": key,
                        "stage": stage or "unknown",
                    }

        return None

    def _visible_in_scopes(self, scopes, phrase):
        for scope in scopes:
            if scope is None:
                continue

            if self._visible_text(scope, phrase):
                return True

            if self._visible_accessible(scope, phrase):
                return True

        return False

    def _visible_text(self, scope, phrase):
        try:
            locator = scope.get_by_text(phrase, exact=False)

            for index in range(locator.count()):
                if locator.nth(index).is_visible(timeout=300):
                    return True
        except Exception:
            return False

        return False

    def _visible_accessible(self, scope, phrase):
        for role in ("alert", "dialog", "status"):
            try:
                locator = scope.get_by_role(role, name=phrase, exact=False)

                for index in range(locator.count()):
                    if locator.nth(index).is_visible(timeout=300):
                        return True
            except Exception:
                continue

        return False


class MockRateLimitDetector:
    """Explicit test hook; never enabled by runtime configuration."""

    def __init__(self, detection_stage="after_navigation", matched_key="limit_post_frequency"):
        self.detection_stage = detection_stage
        self.matched_key = matched_key

    def detect(self, page, dialog=None, stage=None):
        if stage != self.detection_stage:
            return None

        return {
            "matched_key": self.matched_key,
            "stage": stage,
        }
