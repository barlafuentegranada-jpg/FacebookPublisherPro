import threading

from app.services.publish_service import PublishService
from app.services.telegram_service import TelegramService
from app.platforms.base.publish_request import PublishRequest as PlatformPublishRequest


class PublishController:
    def __init__(self, service=None):
        self.service = service or PublishService()
        self.telegram_service = TelegramService()

    def active_context(self):
        return self.service.active_context()

    def telegram_context(self):
        return {
            "accounts": self.telegram_service.list_accounts(),
            "targets": self.telegram_service.list_targets(selected=True),
            "posts": self.service.ready_posts(),
        }

    def build_request(self, *args, **kwargs):
        platform = kwargs.pop("platform", "facebook")

        if platform == "telegram":
            return PlatformPublishRequest(
                platform="telegram",
                account_id=int(kwargs["account_id"]),
                post_id=int(kwargs["post_id"]),
                target_ids=list(kwargs.get("target_ids") or []),
                delay_min=int(kwargs.get("delay_min_seconds") or 0),
                delay_max=int(kwargs.get("delay_max_seconds") or 0),
                dry_run=bool(kwargs.get("dry_run")),
                options={
                    "telegram_parse_mode": kwargs.get("telegram_parse_mode") or None,
                },
            )

        kwargs.pop("account_id", None)
        kwargs.pop("target_ids", None)
        kwargs.pop("telegram_parse_mode", None)
        return self.service.build_request(*args, **kwargs)

    def start_async(self, request, on_progress, on_success, on_error):
        def target():
            try:
                if getattr(request, "platform", None) == "telegram":
                    result = self.telegram_service.publish(request, progress_callback=on_progress)
                else:
                    result = self.service.publish(request, progress=on_progress)
                on_success(result)
            except Exception as error:
                on_error(error)

        threading.Thread(target=target, daemon=True).start()

    def stop(self):
        return self.service.stop()
