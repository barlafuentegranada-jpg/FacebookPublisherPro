from app.services.posts_service import PostsService


class PostsController:
    def __init__(self, service=None):
        self.service = service or PostsService()
        self.search = ""
        self.status = "All"
        self.selected_post_id = None
        self.posts = []

    def load(self):
        self.posts = self.service.list_posts(
            search=self.search,
            status=self.status,
        )
        return self.posts

    def refresh(self):
        posts = self.load()

        if self.selected_post_id and not any(post["id"] == self.selected_post_id for post in posts):
            self.selected_post_id = None

        return posts

    def set_search(self, value):
        self.search = value
        return self.refresh()

    def set_status(self, value):
        self.status = value
        return self.refresh()

    def select_post(self, post_id):
        self.selected_post_id = post_id
        return self.service.get_post(post_id)

    def create_post(self, data):
        post = self.service.create_post(data)
        self.selected_post_id = post["id"]
        self.refresh()
        return post

    def update_selected(self, data):
        if not self.selected_post_id:
            return self.create_post(data)

        post = self.service.update_post(self.selected_post_id, data)
        self.refresh()
        return post

    def save_as_new(self, data):
        post = self.service.create_post(data)
        self.selected_post_id = post["id"]
        self.refresh()
        return post

    def delete_selected(self):
        if not self.selected_post_id:
            raise ValueError("Select a post before deleting.")

        self.service.delete_post(self.selected_post_id)
        self.selected_post_id = None
        return self.refresh()

    def archive_selected(self):
        if not self.selected_post_id:
            raise ValueError("Select a post before archiving.")

        post = self.service.archive_post(self.selected_post_id)
        self.refresh()
        return post

    def duplicate_selected(self):
        if not self.selected_post_id:
            raise ValueError("Select a post before duplicating.")

        post = self.service.duplicate_post(self.selected_post_id)

        if post is None:
            raise ValueError("Post not found.")

        self.selected_post_id = post["id"]
        self.refresh()
        return post
