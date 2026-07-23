from app.database.db import db
from app.platforms.base.platform_adapter import PlatformAdapter
from app.platforms.base.platform_capabilities import PlatformCapabilities
from app.platforms.facebook.facebook_browser import facebook_browser
from app.publisher.result import PublishRequest as FacebookPublishRequest
from app.services.accounts_service import AccountsService
from app.services.groups_service import GroupsService
from app.services.publish_service import PublishService


class FacebookAdapter(PlatformAdapter):
    platform_name = "Facebook"
    platform_key = "facebook"

    def __init__(self, accounts_service=None, groups_service=None, publish_service=None):
        self.accounts_service = accounts_service or AccountsService()
        self.groups_service = groups_service or GroupsService(accounts_service=self.accounts_service)
        self.publish_service = publish_service or PublishService(accounts_service=self.accounts_service)

    def capabilities(self):
        return PlatformCapabilities(
            supports_text=True,
            supports_images=True,
            supports_video=True,
            supports_links=True,
            supports_groups=True,
            supports_pages=False,
            supports_channels=False,
            supports_stories=False,
            supports_reels=False,
            supports_scheduling=False,
            supports_multiple_media=False,
        )

    def validate_account(self, account):
        return {
            "success": bool(account and account.get("platform", "facebook") == self.platform_key),
            "message": "" if account else "Account not found.",
        }

    def check_login(self, account_id):
        try:
            account, status = self.accounts_service.check_login(account_id)
            return {"success": True, "account": account, "status": status}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def open_manual_login(self, account_id):
        try:
            account, message = self.accounts_service.open_manual_login(account_id)
            return {"success": True, "account": account, "message": message}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def scan_targets(self, account_id):
        try:
            account = self.accounts_service.get_account(account_id)

            if not account:
                return {"success": False, "message": "Account not found."}

            self.accounts_service.set_active(account_id)
            targets = self.groups_service.scan_groups()
            return {"success": True, "targets": targets}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def analyze_targets(self, account_id):
        try:
            account = self.accounts_service.get_account(account_id)

            if not account:
                return {"success": False, "message": "Account not found."}

            self.accounts_service.set_active(account_id)
            targets = self.groups_service.analyze_groups()
            return {"success": True, "targets": targets}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def validate_post(self, post):
        try:
            self.publish_service._validate_post_payload(post)
            return {"success": True, "message": "Post is valid for Facebook."}
        except Exception as error:
            return {"success": False, "message": str(error)}

    def publish(self, request, progress_callback=None, stop_event=None):
        try:
            if getattr(request, "platform", "facebook") == "facebook":
                self.accounts_service.set_active(request.account_id)
                if not hasattr(request, "group_ids"):
                    converted = FacebookPublishRequest(
                        account_id=request.account_id,
                        post_id=request.post_id,
                        group_ids=list(request.target_ids or []),
                        delay_min_seconds=getattr(request, "delay_min", 0),
                        delay_max_seconds=getattr(request, "delay_max", 0),
                        stop_on_checkpoint=bool((request.options or {}).get("stop_on_checkpoint", True)),
                        stop_on_block=bool((request.options or {}).get("stop_on_block", True)),
                        dry_run=bool(getattr(request, "dry_run", False)),
                        debug_one_group=False,
                        composer_debug_only=False,
                        stop_after_consecutive_failures=int(
                            (request.options or {}).get(
                                "stop_after_consecutive_failures",
                                5,
                            )
                            or 5
                        ),
                    )
                    converted.campaign_id = (request.options or {}).get("campaign_id")
                    converted.options = request.options or {}
                    request = converted

            return self.publish_service.publish(request, progress=progress_callback)
        except Exception as error:
            return {"success": False, "message": str(error)}

    def close_account(self, account_id):
        state = facebook_browser.get_state()

        if state.get("account_id") != account_id:
            return {"success": True, "message": "Account browser is not active."}

        return facebook_browser.shutdown()
