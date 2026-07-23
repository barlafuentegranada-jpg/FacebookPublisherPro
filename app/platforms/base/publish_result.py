from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class PublishResult:
    platform: str
    account_id: int
    target_id: int
    post_id: int
    status: str = "Pending"
    message: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    finished_at: str = ""
    published_url: str = ""
    metadata: dict = field(default_factory=dict)

    def finish(self, status, message="", published_url=""):
        self.status = status
        self.message = message
        self.published_url = published_url
        self.finished_at = datetime.now().isoformat(timespec="seconds")
        return self

    def to_dict(self):
        return asdict(self)
