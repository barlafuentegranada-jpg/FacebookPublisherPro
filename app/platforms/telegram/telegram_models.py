class TelegramError(Exception):
    code = "Failed"

    def __init__(self, message, metadata=None):
        super().__init__(message)
        self.message = message
        self.metadata = metadata or {}


class InvalidToken(TelegramError):
    code = "InvalidToken"


class ChatNotFound(TelegramError):
    code = "ChatNotFound"


class BotNotMember(TelegramError):
    code = "BotNotMember"


class PermissionDenied(TelegramError):
    code = "PermissionDenied"


class RateLimited(TelegramError):
    code = "RateLimited"


class NetworkError(TelegramError):
    code = "NetworkError"
