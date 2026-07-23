from app.services.targets_service import TargetsService


class TargetsController:
    def __init__(self, service=None):
        self.service = service or TargetsService()
        self.platform_filter = "All Platforms"

    def platforms(self):
        return self.service.platforms()

    def load(self):
        return self.service.targets(self.platform_filter)

    def set_platform(self, platform):
        self.platform_filter = platform
        return self.load()

    def placeholder_message(self):
        return self.service.placeholder_message(self.platform_filter)
