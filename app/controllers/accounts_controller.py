import threading

from app.services.accounts_service import AccountsService
from app.services.telegram_service import TelegramService


class AccountsController:
    """Coordinates account page actions and background browser work."""

    def __init__(self, service=None):
        self.service = service or AccountsService()
        self.telegram_service = TelegramService()

    def list_accounts(self):
        return self.service.list_accounts()

    def add_account(self, name, platform="facebook"):
        return self.service.add_account(name, platform=platform)

    def add_telegram_bot(self, name, token):
        return self.telegram_service.add_bot(name, token)

    def rename_account(self, account_id, name):
        return self.service.rename_account(account_id, name)

    def remove_account(self, account_id):
        account = self.service.get_account(account_id)

        if account and account.get("platform") == "telegram":
            self.telegram_service.remove_account(account_id)
            return

        self.service.remove_account(account_id)

    def reset_login_profile(self, account_id):
        return self.service.reset_login_profile(account_id)

    def set_active(self, account_id):
        return self.service.set_active(account_id)

    def mark_available_after_review(self, account_id, confirmed=False):
        return self.service.mark_available_after_review(account_id, confirmed=confirmed)

    def dashboard_stats(self):
        return self.service.dashboard_stats()

    def active_context(self):
        account = self.service.get_active_account()

        return {
            "account": account,
            "browser_status": self.service.browser_status(),
            "publishing": self.service.is_publishing(),
        }

    def shutdown_browser(self):
        return self.service.shutdown_browser()

    def open_login_async(self, account_id, on_success, on_error):
        self._run_async(
            lambda: self.service.open_manual_login(account_id),
            on_success,
            on_error,
        )

    def open_browser_async(self, account_id, on_success, on_error):
        self._run_async(
            lambda: self.service.open_browser(account_id),
            on_success,
            on_error,
        )

    def refresh_status_async(self, account_id, on_success, on_error):
        account = self.service.get_account(account_id)
        if account and account.get("platform") == "telegram":
            self._run_async(
                lambda: self.telegram_service.check_connection(account_id),
                on_success,
                on_error,
            )
            return

        self._run_async(
            lambda: self.service.check_login(account_id),
            on_success,
            on_error,
        )

    def _run_async(self, task, on_success, on_error):
        def target():
            try:
                result = task()
                on_success(result)
            except Exception as error:
                on_error(error)

        threading.Thread(target=target, daemon=True).start()
