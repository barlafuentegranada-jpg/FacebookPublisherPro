import json

from app.database.db import db
from app.platforms.telegram.telegram_models import BotNotMember, PermissionDenied, TelegramError


class TelegramTargetService:
    def __init__(self, account_service):
        self.account_service = account_service

    def list_targets(self, account_id=None, selected=None):
        return db.get_telegram_targets(account_id=account_id, selected=selected)

    def set_selected(self, target_id, selected):
        db.set_telegram_target_selected(target_id, selected)

    def add_target(self, account_id, chat_identifier):
        account = self.account_service.require_account(account_id)
        client = self.account_service.client_for_account(account)
        chat_id = self._normalize_chat_identifier(chat_identifier)
        chat = client.get_chat(chat_id)
        can_post, status, permission_metadata = self._posting_permission(client, chat)

        if not can_post:
            raise PermissionDenied(status, permission_metadata)

        return db.upsert_telegram_target(
            account_id=account_id,
            target_type=self._target_type(chat),
            external_id=chat.get("id"),
            username=chat.get("username") or "",
            name=chat.get("title") or chat.get("username") or str(chat.get("id")),
            url=self._target_url(chat),
            selected=1,
            active=1,
            can_post=1,
            member_count=chat.get("member_count") or 0,
            status=status,
            metadata={**chat, **permission_metadata},
        )

    def discover_recent_chats(self, account_id):
        account = self.account_service.require_account(account_id)
        client = self.account_service.client_for_account(account)
        updates = client.get_updates(timeout=0)
        discovered = []

        for update in updates:
            chat = self._chat_from_update(update)

            if not chat:
                continue

            try:
                discovered.append(self.add_target(account_id, chat.get("username") or chat.get("id")))
            except TelegramError:
                continue

        return discovered

    def refresh_target(self, target):
        account = self.account_service.require_account(target["account_id"])
        client = self.account_service.client_for_account(account)
        chat = client.get_chat(target["external_id"])
        can_post, status, permission_metadata = self._posting_permission(client, chat)
        return db.upsert_telegram_target(
            account_id=target["account_id"],
            target_type=self._target_type(chat),
            external_id=chat.get("id"),
            username=chat.get("username") or "",
            name=chat.get("title") or chat.get("username") or str(chat.get("id")),
            url=self._target_url(chat),
            selected=target.get("selected", 1),
            active=target.get("active", 1),
            can_post=can_post,
            member_count=chat.get("member_count") or 0,
            status=status,
            metadata={**chat, **permission_metadata},
        )

    def _posting_permission(self, client, chat):
        chat_type = chat.get("type")

        if chat_type == "channel":
            admins = client.get_chat_administrators(chat.get("id"))
            me = client.get_me()
            bot_id = me.get("id")

            for admin in admins:
                user = admin.get("user") or {}

                if user.get("id") == bot_id:
                    can_post = bool(admin.get("can_post_messages") or admin.get("status") == "creator")
                    status = "Can post" if can_post else "Bot is admin but cannot post messages"
                    return can_post, status, {"administrator": admin}

            raise BotNotMember("Bot is not an administrator for this channel.")

        if chat_type in {"group", "supergroup"}:
            return True, "Can post", {"membership": "Bot API access confirmed"}

        return False, f"Unsupported Telegram chat type: {chat_type}", {"chat_type": chat_type}

    def _target_type(self, chat):
        chat_type = chat.get("type")

        if chat_type == "supergroup":
            return "telegram_supergroup"

        if chat_type == "group":
            return "telegram_group"

        return "telegram_channel"

    def _target_url(self, chat):
        username = chat.get("username")

        if username:
            return f"https://t.me/{username}"

        return ""

    def _normalize_chat_identifier(self, value):
        text = str(value or "").strip()

        if text.startswith("@"):
            return text

        try:
            return int(text)
        except ValueError:
            return f"@{text}"

    def _chat_from_update(self, update):
        for key in ["message", "channel_post", "edited_message", "edited_channel_post"]:
            payload = update.get(key) or {}
            chat = payload.get("chat")

            if chat:
                return chat

        return None
