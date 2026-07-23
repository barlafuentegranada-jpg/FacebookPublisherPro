from dataclasses import asdict, dataclass


@dataclass
class PlatformAccount:
    id: int
    platform: str
    name: str
    profile_path: str = ""
    status: str = ""
    active: bool = False
    last_login: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):
        return asdict(self)
