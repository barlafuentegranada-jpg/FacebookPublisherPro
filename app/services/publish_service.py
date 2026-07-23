from pathlib import Path
import time

from app.browser.browser_manager import browser
from app.database.db import db
from app.publisher.result import PublishRequest
from app.services.accounts_service import AccountsService


class PublishService:
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

    def __init__(self, accounts_service=None):
        self.accounts_service = accounts_service or AccountsService()

    def ready_posts(self):
        return db.get_ready_posts()

    def selected_groups(self):
        account = self.accounts_service.get_active_account()

        if account is None:
            return []

        return [dict(group) for group in db.get_selected_groups(account_id=account["id"])]

    def active_context(self):
        account = self.accounts_service.get_active_account()
        return {
            "account": account,
            "groups": self.selected_groups(),
            "posts": self.ready_posts(),
        }

    def build_request(
        self,
        post_id,
        delay_min_seconds,
        delay_max_seconds,
        stop_on_checkpoint,
        stop_on_block,
        dry_run,
        debug_one_group=False,
        composer_debug_only=False,
        stop_after_consecutive_failures=5,
    ):
        account = self.accounts_service.require_active_account()
        delay_min = self._to_int(delay_min_seconds, "Minimum delay")
        delay_max = self._to_int(delay_max_seconds, "Maximum delay")

        if delay_min < 0 or delay_max < 0 or delay_min > delay_max:
            raise ValueError("Delay values must be valid and minimum cannot exceed maximum.")

        selected_groups = self.selected_groups()

        return PublishRequest(
            account_id=account["id"],
            post_id=int(post_id),
            group_ids=[group["id"] for group in selected_groups],
            delay_min_seconds=delay_min,
            delay_max_seconds=delay_max,
            stop_on_checkpoint=bool(stop_on_checkpoint),
            stop_on_block=bool(stop_on_block),
            dry_run=bool(dry_run),
            debug_one_group=bool(debug_one_group),
            composer_debug_only=bool(composer_debug_only),
            stop_after_consecutive_failures=max(
                1,
                self._to_int(
                    stop_after_consecutive_failures,
                    "Stop-after failure count",
                ),
            ),
        )

    def preflight(self, request):
        account = self.accounts_service.require_active_account()

        if account["id"] != request.account_id:
            raise RuntimeError("Publishing account does not match the active account.")

        self.accounts_service.require_publishing_available(account)

        if account.get("login_status") != self.accounts_service.STATUS_LOGGED_IN:
            raise RuntimeError("Active account must be logged in before publishing.")

        if browser.get_state().get("busy"):
            raise RuntimeError(f"Browser is busy: {browser.get_state().get('operation')}")

        post = db.get_post(request.post_id)

        if not post:
            raise RuntimeError("Select a saved post before publishing.")

        post = self._apply_platform_override(post, getattr(request, "options", {}) or {})
        self._log_preflight_post(post)

        if post.get("status") != "Ready":
            raise RuntimeError("Only Ready posts can be published.")

        groups = [
            dict(group)
            for group in db.get_selected_groups(account_id=account["id"])
            if group["id"] in request.group_ids
        ]

        if not groups:
            raise RuntimeError("Select at least one group for the active account.")

        self._validate_post_payload(post)
        return account, post, groups

    def publish(self, request, progress=None):
        account, post, groups = self.preflight(request)
        target_groups = groups[:1] if request.debug_one_group else groups
        self.accounts_service.ensure_active_browser()
        history_ids = self._create_pending_history(
            account,
            post,
            target_groups,
            campaign_id=getattr(request, "campaign_id", None),
        )
        result = browser.publish(
            request,
            account,
            post,
            groups,
            progress=progress,
            history=lambda group_id, status, message="", finished_at=None, published_post_url="": self._update_history(
                history_ids,
                group_id,
                status,
                message,
                finished_at=finished_at,
                published_post_url=published_post_url,
            ),
            rate_limit=lambda details: self.accounts_service.mark_rate_limited(
                account["id"],
                detection_time=details.get("detection_time"),
            ),
        )

        if not result.get("success"):
            for group in target_groups:
                self._fail_pending_history(
                    history_ids,
                    group["id"],
                    result.get("message") or "Publishing run failed.",
                )

        return result

    def stop(self):
        return browser.stop_publish()

    def _validate_post_payload(self, post):
        has_text = bool((post.get("content") or "").strip())
        has_youtube = bool((post.get("youtube_url") or "").strip())
        image_path = post.get("image_path") or ""
        video_path = post.get("video_path") or ""

        if not any([has_text, has_youtube, image_path, video_path]):
            raise RuntimeError("The selected post has no text, media, or YouTube URL.")

        if image_path and video_path:
            raise RuntimeError("Publishing image and video together is not supported in V1.")

        self._validate_media(image_path, self.IMAGE_EXTENSIONS, "image")
        self._validate_media(video_path, self.VIDEO_EXTENSIONS, "video")

    def _validate_media(self, path, extensions, media_type):
        if not path:
            return

        file_path = Path(path)

        if not file_path.exists():
            raise RuntimeError(f"The selected {media_type} file does not exist.")

        if file_path.suffix.lower() not in extensions:
            allowed = ", ".join(sorted(extensions))
            raise RuntimeError(f"Unsupported {media_type} type. Use: {allowed}.")

    def _to_int(self, value, label):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a whole number.")

    def _create_pending_history(self, account, post, groups, campaign_id=None):
        history_ids = {}

        for group in groups:
            history_ids[group["id"]] = db.add_publish_history(
                account_id=account["id"],
                group_id=group["id"],
                post_id=post["id"],
                status="Pending",
                message="Waiting to publish.",
                started_at=self._now(),
                platform="facebook",
                campaign_id=campaign_id,
            )

        return history_ids

    def _update_history(self, history_ids, group_id, status, message="", finished_at=None, published_post_url=""):
        history_id = history_ids.get(group_id)

        if not history_id:
            return

        db.update_publish_history(
            history_id=history_id,
            status=status,
            message=message,
            finished_at=finished_at,
            published_post_url=published_post_url,
        )

    def _fail_pending_history(self, history_ids, group_id, message):
        history_id = history_ids.get(group_id)

        if not history_id:
            return

        row = db.conn.execute(
            "SELECT status FROM publish_history WHERE id=?",
            (history_id,),
        ).fetchone()

        if row and row[0] == "Pending":
            self._update_history(
                history_ids,
                group_id,
                "Failed",
                message,
                finished_at=self._now(),
            )

    def _now(self):
        return db.conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]

    def _log_preflight_post(self, post):
        Path("logs").mkdir(exist_ok=True)
        line = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"post_id={post.get('id')} "
            f"content_length={len(post.get('content') or '')} "
            f"image_path={post.get('image_path') or ''} "
            f"video_path={post.get('video_path') or ''} "
            f"youtube_url_length={len(post.get('youtube_url') or '')}\n"
        )

        with Path("logs/publisher.log").open("a", encoding="utf-8") as log_file:
            log_file.write(line)

    def _apply_platform_override(self, post, options):
        override = options.get("platform_override") or {}

        if not override:
            return post

        merged = dict(post)
        for key in ["content", "image_path", "video_path", "youtube_url", "media_type"]:
            if key in override and override[key] not in (None, ""):
                merged[key] = override[key]

        return merged
