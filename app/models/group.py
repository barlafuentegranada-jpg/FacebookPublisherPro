from dataclasses import dataclass


@dataclass
class Group:

    id: str

    name: str

    url: str

    members: str = ""

    selected: bool = True