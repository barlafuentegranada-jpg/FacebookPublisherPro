from app.platforms.base.platform_registry import platform_registry
from app.platforms.facebook import FacebookAdapter
from app.platforms.instagram import InstagramAdapter
from app.platforms.telegram.telegram_adapter import TelegramAdapter

platform_registry.register(FacebookAdapter(), enabled=True)
platform_registry.register(InstagramAdapter(), enabled=False)
platform_registry.register(TelegramAdapter(), enabled=True)

__all__ = ["platform_registry"]
