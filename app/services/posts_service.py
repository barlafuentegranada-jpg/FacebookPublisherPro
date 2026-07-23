from pathlib import Path

from app.database.db import db


class PostsService:
    STATUSES = ["Draft", "Ready", "Archived"]
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

    def list_posts(self, search=None, status=None, tag=None):
        return db.get_posts(search=search, status=status, tag=tag)

    def get_post(self, post_id):
        return db.get_post(post_id)

    def create_post(self, data):
        payload = self._clean(data)
        self._validate(payload)
        return db.create_post(**payload)

    def update_post(self, post_id, data):
        payload = self._clean(data)
        self._validate(payload)
        return db.update_post(post_id, **payload)

    def delete_post(self, post_id):
        db.delete_post(post_id)

    def archive_post(self, post_id):
        return db.archive_post(post_id)

    def duplicate_post(self, post_id):
        return db.duplicate_post(post_id)

    def count_posts(self, status=None):
        return db.count_posts(status=status)

    def _clean(self, data):
        return {
            "title": str(data.get("title") or "").strip(),
            "content": str(data.get("content") or "").strip(),
            "image_path": str(data.get("image_path") or "").strip(),
            "video_path": str(data.get("video_path") or "").strip(),
            "youtube_url": str(data.get("youtube_url") or "").strip(),
            "tags": str(data.get("tags") or "").strip(),
            "status": str(data.get("status") or "Draft").strip() or "Draft",
            "supported_platforms": data.get("supported_platforms") or ["facebook"],
            "platform_overrides": data.get("platform_overrides") or {},
            "media_type": data.get("media_type") or self._media_type(data),
            "metadata": data.get("metadata") or {},
        }

    def _media_type(self, data):
        if data.get("video_path"):
            return "video"

        if data.get("image_path"):
            return "image"

        if data.get("youtube_url"):
            return "link"

        return "text"

    def _validate(self, data):
        if data["status"] not in self.STATUSES:
            raise ValueError("Choose a valid post status.")

        if not any(
            [
                data["content"],
                data["image_path"],
                data["video_path"],
                data["youtube_url"],
            ]
        ):
            raise ValueError("Add text, an image, a video, or a YouTube URL before saving.")

        self._validate_media_path(data["image_path"], self.IMAGE_EXTENSIONS, "image")
        self._validate_media_path(data["video_path"], self.VIDEO_EXTENSIONS, "video")

    def _validate_media_path(self, path, extensions, media_type):
        if not path:
            return

        file_path = Path(path)

        if not file_path.exists():
            raise ValueError(f"The selected {media_type} file does not exist.")

        if file_path.suffix.lower() not in extensions:
            allowed = ", ".join(sorted(extensions))
            raise ValueError(f"Unsupported {media_type} file type. Use: {allowed}.")
