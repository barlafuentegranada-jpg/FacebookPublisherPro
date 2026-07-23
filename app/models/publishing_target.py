from dataclasses import asdict, dataclass, field


@dataclass
class PublishingTarget:
    id: int
    platform: str
    account_id: int
    target_type: str
    external_id: str = ""
    name: str = ""
    url: str = ""
    members_count: int = 0
    privacy: str = ""
    category: str = ""
    selected: bool = False
    active: bool = True
    metadata: dict = field(default_factory=dict)
    last_scan: str = ""

    def to_dict(self):
        return asdict(self)
