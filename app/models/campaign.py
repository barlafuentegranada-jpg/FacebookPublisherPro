from dataclasses import asdict, dataclass


CAMPAIGN_STATUSES = [
    "Draft",
    "Ready",
    "Running",
    "Stopping",
    "Completed",
    "CompletedWithErrors",
    "Stopped",
    "Failed",
    "Archived",
]


@dataclass
class Campaign:
    id: int = None
    name: str = ""
    description: str = ""
    status: str = "Draft"
    post_id: int = None
    delay_min_seconds: int = 0
    delay_max_seconds: int = 0
    stop_on_error: bool = False
    stop_on_checkpoint: bool = True
    continue_other_platforms_after_facebook_rate_limit: bool = False
    created_at: str = ""
    updated_at: str = ""
    last_started_at: str = ""
    last_finished_at: str = ""

    def to_dict(self):
        return asdict(self)
