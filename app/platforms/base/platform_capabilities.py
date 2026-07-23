from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PlatformCapabilities:
    supports_text: bool = False
    supports_images: bool = False
    supports_video: bool = False
    supports_links: bool = False
    supports_groups: bool = False
    supports_pages: bool = False
    supports_channels: bool = False
    supports_stories: bool = False
    supports_reels: bool = False
    supports_scheduling: bool = False
    supports_multiple_media: bool = False

    def to_dict(self):
        return asdict(self)
