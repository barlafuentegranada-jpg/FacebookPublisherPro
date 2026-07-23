import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

try:
    import requests
except ImportError:  # pragma: no cover - fallback keeps the app usable before dependency install.
    requests = None

from app.platforms.telegram.telegram_models import (
    BotNotMember,
    ChatNotFound,
    InvalidToken,
    NetworkError,
    PermissionDenied,
    RateLimited,
    TelegramError,
)


class TelegramClient:
    API_ROOT = "https://api.telegram.org"

    def __init__(self, token, timeout=20):
        self.token = token
        self.timeout = timeout

    def get_me(self):
        return self._request("getMe")

    def get_chat(self, chat_id):
        return self._request("getChat", {"chat_id": chat_id})

    def get_chat_administrators(self, chat_id):
        return self._request("getChatAdministrators", {"chat_id": chat_id})

    def send_message(self, chat_id, text, parse_mode=None):
        payload = {"chat_id": chat_id, "text": text}

        if parse_mode:
            payload["parse_mode"] = parse_mode

        return self._request("sendMessage", payload)

    def send_photo(self, chat_id, photo_path, caption=None, parse_mode=None):
        payload = {"chat_id": chat_id}

        if caption:
            payload["caption"] = caption

        if parse_mode:
            payload["parse_mode"] = parse_mode

        return self._multipart("sendPhoto", payload, "photo", photo_path)

    def send_video(self, chat_id, video_path, caption=None, parse_mode=None):
        payload = {"chat_id": chat_id}

        if caption:
            payload["caption"] = caption

        if parse_mode:
            payload["parse_mode"] = parse_mode

        return self._multipart("sendVideo", payload, "video", video_path)

    def send_media_group(self, chat_id, media):
        return self._request("sendMediaGroup", {"chat_id": chat_id, "media": json.dumps(media)})

    def get_updates(self, offset=None, timeout=0):
        payload = {"timeout": timeout}

        if offset is not None:
            payload["offset"] = offset

        return self._request("getUpdates", payload)

    def _request(self, method, payload=None):
        if requests:
            return self._requests_call(method, payload or {})

        data = urllib.parse.urlencode(payload or {}).encode("utf-8")
        request = urllib.request.Request(self._url(method), data=data, method="POST")
        return self._open(request)

    def _multipart(self, method, payload, file_field, file_path):
        if requests:
            with open(file_path, "rb") as file_handle:
                return self._requests_call(
                    method,
                    payload,
                    files={file_field: (os.path.basename(file_path), file_handle)},
                )

        boundary = f"----SocialPublisher{uuid.uuid4().hex}"
        body = bytearray()

        for key, value in payload.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")

        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))

        with open(file_path, "rb") as file_handle:
            body.extend(file_handle.read())

        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        request = urllib.request.Request(
            self._url(method),
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        return self._open(request)

    def _requests_call(self, method, payload, files=None):
        try:
            response = requests.post(
                self._url(method),
                data=payload,
                files=files,
                timeout=self.timeout,
            )
            data = response.json()
        except requests.RequestException as error:
            raise NetworkError(self._sanitize_error(error))
        except ValueError:
            raise NetworkError("Telegram returned an invalid JSON response.")

        if not data.get("ok"):
            self._raise_api_error(data)

        return data.get("result")

    def _open(self, request):
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            self._raise_api_error(self._parse_error(body, error.code))
        except urllib.error.URLError as error:
            raise NetworkError(self._sanitize_error(error.reason))

        if not data.get("ok"):
            self._raise_api_error(data)

        return data.get("result")

    def _raise_api_error(self, data):
        description = self._sanitize_error(data.get("description") or "Telegram request failed")
        parameters = data.get("parameters") or {}
        retry_after = parameters.get("retry_after")
        metadata = {"retry_after": retry_after} if retry_after is not None else {}
        lower = description.lower()

        if retry_after is not None:
            raise RateLimited(description, metadata)

        if "unauthorized" in lower or "token" in lower:
            raise InvalidToken(description, metadata)

        if "chat not found" in lower:
            raise ChatNotFound(description, metadata)

        if "bot is not a member" in lower or "not enough rights" in lower:
            raise BotNotMember(description, metadata)

        if "forbidden" in lower or "not allowed" in lower or "have no rights" in lower:
            raise PermissionDenied(description, metadata)

        raise TelegramError(description, metadata)

    def _parse_error(self, body, status_code):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "error_code": status_code, "description": "Telegram HTTP request failed"}

    def _url(self, method):
        return f"{self.API_ROOT}/bot{self.token}/{method}"

    def _sanitize_error(self, value):
        text = str(value)

        if self.token:
            text = text.replace(self.token, "[redacted-token]")

        return text.replace(self._url(""), f"{self.API_ROOT}/bot[redacted-token]/")[:1000]
