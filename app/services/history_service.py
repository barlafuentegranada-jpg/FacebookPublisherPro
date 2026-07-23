from app.database.db import db


class HistoryService:
    STATUSES = [
        "All",
        "Pending",
        "Preparing",
        "Navigating",
        "PageReady",
        "Opening",
        "OpeningComposer",
        "ComposerOpened",
        "InsertingContent",
        "ContentVerified",
        "ContentInserted",
        "UploadingMedia",
        "MediaUploaded",
        "ReadyToSubmit",
        "Submitting",
        "Verifying",
        "Success",
        "Failed",
        "PermissionDenied",
        "Checkpoint",
        "Blocked",
        "Stopped",
        "Validated",
        "ValidationFailed",
        "InvalidToken",
        "ChatNotFound",
        "BotNotMember",
        "RateLimited",
        "NetworkError",
    ]

    PLATFORMS = ["All", "facebook", "instagram", "telegram"]

    def accounts(self):
        rows = db.conn.execute(
            """
            SELECT id, name
            FROM accounts
            ORDER BY name
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def campaigns(self):
        return db.get_campaigns(include_archived=True)

    def platforms(self):
        return self.PLATFORMS

    def history(self, account_id=None, status=None, date=None, platform=None, campaign_id=None):
        return db.get_publish_history(
            account_id=account_id,
            status=status,
            date=date,
            platform=platform,
            campaign_id=campaign_id,
        )
