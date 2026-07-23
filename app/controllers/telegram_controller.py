import threading

from app.services.telegram_service import TelegramService


class TelegramController:
    def __init__(self, service=None):
        self.service = service or TelegramService()

    def accounts(self):
        return self.service.list_accounts()

    def targets(self, account_id=None):
        return self.service.list_targets(account_id=account_id)

    def add_bot(self, name, token):
        return self.service.add_bot(name, token)

    def check_connection(self, account_id):
        return self.service.check_connection(account_id)

    def remove_account(self, account_id):
        return self.service.remove_account(account_id)

    def add_target(self, account_id, chat_identifier):
        return self.service.add_target(account_id, chat_identifier)

    def discover_recent_chats(self, account_id):
        return self.service.discover_recent_chats(account_id)

    def set_target_selected(self, target_id, selected):
        return self.service.set_target_selected(target_id, selected)

    def send_test_message(self, account_id, target_id, text):
        return self.service.send_test_message(account_id, target_id, text)

    def run_async(self, task, on_success, on_error):
        def target():
            try:
                on_success(task())
            except Exception as error:
                on_error(error)

        threading.Thread(target=target, daemon=True).start()
