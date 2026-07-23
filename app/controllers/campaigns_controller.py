import threading

from app.services.campaigns_service import CampaignsService
from app.workers.campaign_worker import CampaignWorker


class CampaignsController:
    def __init__(self, service=None):
        self.service = service or CampaignsService()
        self.worker = None

    def load(self):
        return self.service.campaigns()

    def get(self, campaign_id):
        return self.service.get(campaign_id)

    def create(self):
        return self.service.create()

    def save(self, campaign_id, data):
        return self.service.save(campaign_id, data)

    def duplicate(self, campaign_id):
        return self.service.duplicate(campaign_id)

    def delete(self, campaign_id):
        self.service.delete(campaign_id)

    def archive(self, campaign_id):
        return self.service.archive(campaign_id)

    def validate(self, campaign_id):
        return self.service.validate(campaign_id)

    def ready_posts(self):
        return self.service.ready_posts()

    def enabled_platforms(self):
        return self.service.enabled_platforms()

    def available_accounts(self):
        return self.service.available_accounts()

    def available_targets(self, account_ids=None):
        return self.service.available_targets(account_ids=account_ids)

    def runs(self, campaign_id=None):
        return self.service.runs(campaign_id)

    def start_async(self, campaign_id, on_progress, on_success, on_error):
        if self.worker and self.worker.is_running():
            raise RuntimeError("A campaign is already running.")

        validation = self.service.validate(campaign_id)

        if not validation["valid"]:
            raise RuntimeError(" | ".join(validation["errors"]))

        self.worker = CampaignWorker(campaign_id)

        def target():
            try:
                result = self.worker.run(progress_callback=on_progress)
                on_success(result)
            except Exception as error:
                on_error(error)

        threading.Thread(target=target, daemon=True).start()

    def stop(self):
        if self.worker:
            self.worker.stop()
