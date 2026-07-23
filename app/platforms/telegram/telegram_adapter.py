from app.platforms.base.platform_adapter import PlatformAdapter
from app.platforms.base.platform_capabilities import PlatformCapabilities


class TelegramAdapter(PlatformAdapter):
    platform_name = "Telegram"
    platform_key = "telegram"

    def __init__(self, service=None):
        self._service = service

    @property
    def service(self):
        if self._service is None:
            from app.services.telegram_service import TelegramService

            self._service = TelegramService()

        return self._service

    def capabilities(self):
        return PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_video=True,
            supports_links=True,
            supports_groups=True,
            supports_pages=False,
            supports_channels=True,
            supports_stories=False,
            supports_reels=False,
            supports_scheduling=False,
            supports_multiple_media=False,
        )

    def validate_account(self, account):
        if not account or account.get("platform") != "telegram":
            return {"success": False, "status": "Failed", "message": "Telegram account not found."}

        return {"success": True, "status": account.get("status") or "Connected", "message": "Telegram account is available."}

    def check_login(self, account_id):
        try:
            account = self.service.check_connection(account_id)
            return {"success": True, "status": "Connected", "account": account}
        except Exception as error:
            return self.service.accounts.structured_error(error)

    def open_manual_login(self, account_id):
        return {"success": False, "status": "Failed", "message": "Telegram Bot API does not use manual browser login."}

    def scan_targets(self, account_id):
        try:
            targets = self.service.discover_recent_chats(account_id)
            return {"success": True, "targets": targets}
        except Exception as error:
            return self.service.accounts.structured_error(error)

    def analyze_targets(self, account_id):
        return {"success": True, "targets": self.service.list_targets(account_id=account_id)}

    def validate_post(self, post):
        if not post:
            return {"success": False, "status": "Failed", "message": "Post not found."}

        if post.get("image_path") and post.get("video_path"):
            return {"success": False, "status": "Failed", "message": "Telegram V1 supports one image or one video, not both."}

        return {"success": True, "message": "Post is valid for Telegram."}

    def publish(self, request, progress_callback=None, stop_event=None):
        try:
            return self.service.publish(request, progress_callback=progress_callback, stop_event=stop_event)
        except Exception as error:
            return self.service.accounts.structured_error(error)

    def close_account(self, account_id):
        return {"success": True, "message": "Telegram Bot API has no browser session to close."}
