import json
from pathlib import Path

from app.database.db import db
from app.platforms.base.publish_result import PublishResult
from app.platforms.telegram.telegram_models import TelegramError


class TelegramPublisher:
    CAPTION_LIMIT = 1024
    MESSAGE_LIMIT = 4096

    MARKDOWN_V2_CHARS = r"_*[]()~`>#+-=|{}.!"

    def __init__(self, account_service):
        self.account_service = account_service

    def publish(self, request, progress_callback=None, stop_event=None):
        account = self.account_service.require_account(request.account_id)
        client = self.account_service.client_for_account(account)
        post = db.get_post(request.post_id)

        if not post:
            raise ValueError("Post not found.")

        post = self._apply_platform_override(post, request.options or {})
        results = []
        target_ids = request.target_ids or []

        for target_id in target_ids:
            if stop_event and stop_event.is_set():
                break

            target = db.get_telegram_target(target_id)
            result = self._publish_target(client, request, post, target)
            results.append(result.to_dict())

            if progress_callback:
                progress_callback({"event": "result", "data": result.to_dict()})

        return {
            "success": all(item["status"] == "Success" for item in results) if results else False,
            "operation": "telegram publishing",
            "message": "Telegram publishing finished",
            "data": {
                "results": results,
                "success_count": sum(1 for item in results if item["status"] == "Success"),
                "failure_count": sum(1 for item in results if item["status"] != "Success"),
                "skipped_count": 0,
            },
        }

    def _publish_target(self, client, request, post, target):
        if not target:
            return PublishResult(
                platform="telegram",
                account_id=request.account_id,
                target_id=0,
                post_id=request.post_id,
            ).finish("ChatNotFound", "Telegram target not found.")

        result = PublishResult(
            platform="telegram",
            account_id=request.account_id,
            target_id=target["id"],
            post_id=request.post_id,
        )
        history_id = db.add_publish_history(
            account_id=request.account_id,
            group_id=target["id"],
            post_id=request.post_id,
            status="Pending",
            message="Waiting to publish.",
            platform="telegram",
            campaign_id=(request.options or {}).get("campaign_id"),
            metadata={"chat_id": target["external_id"]},
        )

        try:
            response_metadata = self._send(client, post, target, request.options or {})
            result.finish("Success", "Telegram message sent.", self._published_url(target, response_metadata))
            result.metadata = response_metadata
            db.update_publish_history(
                history_id,
                "Success",
                result.message,
                finished_at=result.finished_at,
                published_post_url=result.published_url,
                metadata={**response_metadata, "publish_history_id": history_id},
            )
            result.metadata["publish_history_id"] = history_id
        except TelegramError as error:
            result.finish(error.code, error.message)
            result.metadata = {**error.metadata, "publish_history_id": history_id}
            db.update_publish_history(
                history_id,
                error.code,
                error.message,
                finished_at=result.finished_at,
                metadata=result.metadata,
            )
        except Exception as error:
            result.finish("Failed", str(error))
            result.metadata = {"publish_history_id": history_id}
            db.update_publish_history(history_id, "Failed", result.message, finished_at=result.finished_at)

        return result

    def _send(self, client, post, target, options):
        chat_id = target["external_id"]
        parse_mode = options.get("telegram_parse_mode") or None
        text = self._formatted_text(post, parse_mode)
        image_path = post.get("image_path") or ""
        video_path = post.get("video_path") or ""

        if image_path:
            self._ensure_file(image_path)
            caption, remaining = self._caption_parts(text)
            message = client.send_photo(chat_id, image_path, caption=caption, parse_mode=parse_mode)
            metadata = self._message_metadata(message, chat_id)

            if remaining:
                followup = client.send_message(chat_id, remaining, parse_mode=parse_mode)
                metadata["followup_message_id"] = followup.get("message_id")

            return metadata

        if video_path:
            self._ensure_file(video_path)
            caption, remaining = self._caption_parts(text)
            message = client.send_video(chat_id, video_path, caption=caption, parse_mode=parse_mode)
            metadata = self._message_metadata(message, chat_id)

            if remaining:
                followup = client.send_message(chat_id, remaining, parse_mode=parse_mode)
                metadata["followup_message_id"] = followup.get("message_id")

            return metadata

        message = client.send_message(chat_id, text[: self.MESSAGE_LIMIT], parse_mode=parse_mode)
        metadata = self._message_metadata(message, chat_id)
        remaining = text[self.MESSAGE_LIMIT :]

        if remaining:
            followup = client.send_message(chat_id, remaining[: self.MESSAGE_LIMIT], parse_mode=parse_mode)
            metadata["followup_message_id"] = followup.get("message_id")

        return metadata

    def _formatted_text(self, post, parse_mode):
        parts = []

        if post.get("content"):
            parts.append(post["content"].strip())

        if post.get("youtube_url"):
            parts.append(post["youtube_url"].strip())

        text = "\n\n".join(parts).strip()

        if parse_mode == "MarkdownV2":
            return self._escape_markdown_v2(text)

        return text

    def _caption_parts(self, text):
        if len(text) <= self.CAPTION_LIMIT:
            return text, ""

        return text[: self.CAPTION_LIMIT], text[self.CAPTION_LIMIT :]

    def _message_metadata(self, message, chat_id):
        return {
            "message_id": message.get("message_id"),
            "chat_id": chat_id,
            "date": message.get("date"),
        }

    def _published_url(self, target, metadata):
        username = target.get("username")
        message_id = metadata.get("message_id")

        if username and message_id:
            return f"https://t.me/{username}/{message_id}"

        return ""

    def _escape_markdown_v2(self, text):
        return "".join(f"\\{char}" if char in self.MARKDOWN_V2_CHARS else char for char in text)

    def _ensure_file(self, path):
        if not Path(path).exists():
            raise ValueError(f"Media file does not exist: {path}")

    def _apply_platform_override(self, post, options):
        override = options.get("platform_override") or {}

        if not override:
            return post

        merged = dict(post)
        for key in ["content", "image_path", "video_path", "youtube_url", "media_type"]:
            if key in override and override[key] not in (None, ""):
                merged[key] = override[key]

        return merged
