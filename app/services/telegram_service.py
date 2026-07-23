from app.platforms.telegram.telegram_account_service import TelegramAccountService
from app.platforms.telegram.telegram_target_service import TelegramTargetService
from app.platforms.telegram.telegram_publisher import TelegramPublisher


class TelegramService:
    def __init__(self):
        self.accounts = TelegramAccountService()
        self.targets = TelegramTargetService(self.accounts)
        self.publisher = TelegramPublisher(self.accounts)

    def list_accounts(self):
        return self.accounts.list_accounts()

    def add_bot(self, name, token):
        return self.accounts.add_bot(name, token)

    def check_connection(self, account_id):
        return self.accounts.check_connection(account_id)

    def remove_account(self, account_id):
        return self.accounts.remove_account(account_id)

    def list_targets(self, account_id=None, selected=None):
        return self.targets.list_targets(account_id=account_id, selected=selected)

    def add_target(self, account_id, chat_identifier):
        return self.targets.add_target(account_id, chat_identifier)

    def discover_recent_chats(self, account_id):
        return self.targets.discover_recent_chats(account_id)

    def set_target_selected(self, target_id, selected):
        return self.targets.set_selected(target_id, selected)

    def send_test_message(self, account_id, target_id, text):
        from app.platforms.base.publish_request import PublishRequest
        from app.database.db import db

        post = db.create_post(
            title="Telegram Test Message",
            content=text,
            status="Ready",
            supported_platforms=["telegram"],
            media_type="text",
        )
        request = PublishRequest(
            platform="telegram",
            account_id=account_id,
            post_id=post["id"],
            target_ids=[target_id],
            delay_min=0,
            delay_max=0,
            dry_run=False,
            options={"telegram_parse_mode": None},
        )
        return self.publisher.publish(request)

    def publish(self, request, progress_callback=None, stop_event=None):
        return self.publisher.publish(request, progress_callback=progress_callback, stop_event=stop_event)
