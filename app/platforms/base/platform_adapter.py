from abc import ABC, abstractmethod


class PlatformAdapter(ABC):
    @property
    @abstractmethod
    def platform_name(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def platform_key(self):
        raise NotImplementedError

    @abstractmethod
    def capabilities(self):
        raise NotImplementedError

    @abstractmethod
    def validate_account(self, account):
        raise NotImplementedError

    @abstractmethod
    def check_login(self, account_id):
        raise NotImplementedError

    @abstractmethod
    def open_manual_login(self, account_id):
        raise NotImplementedError

    @abstractmethod
    def scan_targets(self, account_id):
        raise NotImplementedError

    @abstractmethod
    def analyze_targets(self, account_id):
        raise NotImplementedError

    @abstractmethod
    def validate_post(self, post):
        raise NotImplementedError

    @abstractmethod
    def publish(self, request, progress_callback=None, stop_event=None):
        raise NotImplementedError

    @abstractmethod
    def close_account(self, account_id):
        raise NotImplementedError
