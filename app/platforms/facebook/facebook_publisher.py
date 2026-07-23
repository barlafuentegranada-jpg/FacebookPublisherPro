from app.services.publish_service import PublishService


class FacebookPublisher:
    def __init__(self, service=None):
        self.service = service or PublishService()

    def publish(self, request, progress_callback=None, stop_event=None):
        return self.service.publish(request, progress=progress_callback)
