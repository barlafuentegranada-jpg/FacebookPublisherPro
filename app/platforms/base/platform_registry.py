class PlatformRegistry:
    def __init__(self):
        self._adapters = {}
        self._enabled = set()

    def register(self, adapter, enabled=False):
        self._adapters[adapter.platform_key] = adapter

        if enabled:
            self._enabled.add(adapter.platform_key)

    def get(self, platform_key):
        adapter = self._adapters.get(platform_key)

        if adapter is None:
            raise KeyError(f"Unknown platform: {platform_key}")

        return adapter

    def platforms(self):
        return [
            {
                "key": key,
                "name": adapter.platform_name,
                "enabled": key in self._enabled,
                "capabilities": adapter.capabilities().to_dict(),
            }
            for key, adapter in self._adapters.items()
        ]

    def enabled_platforms(self):
        return [item for item in self.platforms() if item["enabled"]]

    def is_enabled(self, platform_key):
        return platform_key in self._enabled

    def enabled_adapters(self):
        return [
            self._adapters[key]
            for key in sorted(self._enabled)
            if key in self._adapters
        ]

    def capabilities(self, platform_key):
        return self.get(platform_key).capabilities()


platform_registry = PlatformRegistry()
