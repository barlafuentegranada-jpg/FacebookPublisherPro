from pathlib import Path


class MediaUploader:
    PREVIEW_SELECTORS = [
        "img",
        "video",
        "[aria-label*='Remove']",
        "[aria-label*='إزالة']",
        "[role='progressbar']",
    ]

    def upload(self, dialog, post):
        files = [path for path in [post.get("image_path"), post.get("video_path")] if path]

        if not files:
            return True, "No media selected."

        inputs = dialog.locator("input[type='file']")

        if inputs.count() == 0:
            return False, "Facebook composer did not expose a media file picker."

        input_locator = inputs.first
        input_locator.set_input_files(files, timeout=15000)

        if self._wait_for_upload_signal(dialog):
            return True, "Media uploaded."

        return False, "Media upload confirmation was not detected."

    def validate_media(self, post):
        image_path = post.get("image_path") or ""
        video_path = post.get("video_path") or ""

        if image_path and video_path:
            return False, "Publishing image and video together is not supported in V1."

        for path in [image_path, video_path]:
            if path and not Path(path).exists():
                return False, f"Media file is missing: {path}"

        return True, "Media validated."

    def _wait_for_upload_signal(self, dialog):
        for _attempt in range(20):
            for selector in self.PREVIEW_SELECTORS:
                try:
                    if dialog.locator(selector).count() > 0:
                        return True
                except Exception:
                    continue

            try:
                dialog.page.wait_for_timeout(500)
            except Exception:
                return False

        return False
