from app.platforms.base.platform_adapter import PlatformAdapter
from app.platforms.base.platform_capabilities import PlatformCapabilities


class InstagramAdapter(PlatformAdapter):
    platform_name = "Instagram"
    platform_key = "instagram"

    def capabilities(self):
        return PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_video=True,
            supports_links=False,
            supports_groups=False,
            supports_pages=False,
            supports_channels=False,
            supports_stories=True,
            supports_reels=True,
            supports_scheduling=False,
            supports_multiple_media=False,
        )

    def _not_implemented(self):
        return {"success": False, "message": "Platform not implemented yet"}

    def validate_account(self, account):
        return self._not_implemented()

    def check_login(self, account_id):
        return self._not_implemented()

    def open_manual_login(self, account_id):
        return self._not_implemented()

    def scan_targets(self, account_id):
        return self._not_implemented()

    def analyze_targets(self, account_id):
        return self._not_implemented()

    def validate_post(self, post):
        return self._not_implemented()

    def publish(self, request, progress_callback=None, stop_event=None):
        return self._not_implemented()

    def close_account(self, account_id):
        return self._not_implemented()
