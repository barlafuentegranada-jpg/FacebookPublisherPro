from dataclasses import asdict, dataclass, field
from datetime import datetime


STATUSES = [
    "Pending",
    "Preparing",
    "Navigating",
    "PageReady",
    "OpeningComposer",
    "Success",
    "Failed",
    "PermissionDenied",
    "Checkpoint",
    "Blocked",
    "RateLimited",
    "Stopped",
    "Validated",
    "ValidationFailed",
    "ComposerOpened",
    "InsertingContent",
    "ContentVerified",
    "UploadingMedia",
    "MediaUploaded",
    "ReadyToSubmit",
    "Submitting",
    "Verifying",
]


@dataclass
class PublishRequest:
    account_id: int
    post_id: int
    group_ids: list
    delay_min_seconds: int
    delay_max_seconds: int
    stop_on_checkpoint: bool = True
    stop_on_block: bool = True
    dry_run: bool = False
    debug_one_group: bool = False
    composer_debug_only: bool = False
    stop_after_consecutive_failures: int = 5


@dataclass
class PublishResult:
    group_id: int
    group_name: str
    group_url: str
    status: str = "Pending"
    message: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    finished_at: str = ""
    published_post_url: str = ""
    data: dict = field(default_factory=dict)

    def finish(self, status, message="", published_post_url=""):
        self.status = status
        self.message = message
        self.published_post_url = published_post_url
        self.finished_at = datetime.now().isoformat(timespec="seconds")
        return self

    def to_dict(self):
        return asdict(self)
