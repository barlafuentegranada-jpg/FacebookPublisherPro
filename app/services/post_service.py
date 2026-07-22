from pathlib import Path


class PostService:

    def __init__(self):

        self.clear()

    # =====================================

    def clear(self):

        self.title = ""

        self.content = ""

        self.image_path = ""

        self.video_path = ""

        self.youtube_url = ""

        self.delay = 30

    # =====================================

    def set_title(self, title):

        self.title = title.strip()

    # =====================================

    def set_content(self, content):

        self.content = content.strip()

    # =====================================

    def set_image(self, path):

        if path:

            self.image_path = str(Path(path))

    # =====================================

    def set_video(self, path):

        if path:

            self.video_path = str(Path(path))

    # =====================================

    def set_youtube(self, url):

        self.youtube_url = url.strip()

    # =====================================

    def set_delay(self, seconds):

        try:

            self.delay = int(seconds)

        except:

            self.delay = 30

    # =====================================

    def has_image(self):

        return self.image_path != ""

    # =====================================

    def has_video(self):

        return self.video_path != ""

    # =====================================

    def has_youtube(self):

        return self.youtube_url != ""

    # =====================================

    def has_content(self):

        return self.content != ""

    # =====================================

    def is_ready(self):

        return (
            self.has_content()
            or self.has_image()
            or self.has_video()
            or self.has_youtube()
        )

    # =====================================

    def to_dict(self):

        return {

            "title": self.title,

            "content": self.content,

            "image": self.image_path,

            "video": self.video_path,

            "youtube": self.youtube_url,

            "delay": self.delay
        }


post_service = PostService()