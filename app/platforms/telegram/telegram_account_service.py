import re

from app.database.db import db
from app.platforms.telegram.telegram_client import TelegramClient
from app.platforms.telegram.telegram_models import TelegramError
from app.services.secret_store import secret_store


class TelegramAccountService:
    TOKEN_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")

    def list_accounts(self):
        return db.get_telegram_accounts()

    def add_bot(self, name, token):
        clean_name = str(name or "").strip()
        clean_token = str(token or "").strip()

        if not clean_name:
            raise ValueError("Bot display name is required.")

        if not self.TOKEN_PATTERN.match(clean_token):
            raise ValueError("Invalid Telegram bot token format.")

        client = TelegramClient(clean_token)
        me = client.get_me()
        bot_id = me.get("id")
        username = me.get("username") or ""
        secret_reference = f"telegram_bot:{bot_id}"
        secret_store.set_secret(secret_reference, clean_token)
        return db.add_telegram_account(
            name=clean_name,
            bot_id=bot_id,
            bot_username=username,
            secret_reference=secret_reference,
            status="Connected",
        )

    def check_connection(self, account_id):
        account = self.require_account(account_id)
        client = self.client_for_account(account)
        me = client.get_me()
        return db.update_telegram_account_status(
            account_id,
            "Connected",
            bot_username=me.get("username") or "",
            bot_id=me.get("id"),
        )

    def remove_account(self, account_id):
        account = self.require_account(account_id)
        secret_store.delete_secret(account["encrypted_token_reference"])
        db.delete_telegram_account(account_id)

    def require_account(self, account_id):
        account = db.get_telegram_account(account_id)

        if not account:
            raise ValueError("Telegram account not found.")

        return account

    def client_for_account(self, account):
        token = secret_store.get_secret(account["encrypted_token_reference"])

        if not token:
            raise ValueError("Telegram bot token is not available in the secret store.")

        return TelegramClient(token)

    def structured_error(self, error):
        if isinstance(error, TelegramError):
            return {"success": False, "status": error.code, "message": error.message, "metadata": error.metadata}

        return {"success": False, "status": "Failed", "message": str(error), "metadata": {}}
