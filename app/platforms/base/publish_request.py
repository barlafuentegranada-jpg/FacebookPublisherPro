from dataclasses import asdict, dataclass, field


@dataclass
class PublishRequest:
    platform: str
    account_id: int
    post_id: int
    target_ids: list
    delay_min: int
    delay_max: int
    dry_run: bool = False
    options: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
