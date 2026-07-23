import json
import random
import threading
import time

from app.database.db import db
from app.platforms import platform_registry
from app.platforms.base.publish_request import PublishRequest


class CampaignWorker:
    FAILURE_STATUSES = {
        "Failed",
        "PermissionDenied",
        "Checkpoint",
        "Blocked",
        "InvalidToken",
        "ChatNotFound",
        "BotNotMember",
        "RateLimited",
        "NetworkError",
    }

    def __init__(self, campaign_id):
        self.campaign_id = campaign_id
        self.stop_event = threading.Event()
        self._running = False

    def is_running(self):
        return self._running

    def stop(self):
        self.stop_event.set()
        campaign = db.get_campaign(self.campaign_id)
        if campaign and campaign.get("status") == "Running":
            db.update_campaign(self.campaign_id, status="Stopping")

    def run(self, progress_callback=None):
        campaign = db.get_campaign(self.campaign_id)

        if not campaign:
            raise RuntimeError("Campaign not found.")

        targets = self._ordered_targets(campaign["id"])
        run = db.create_campaign_run(campaign["id"], len(targets))
        db.update_campaign(campaign["id"], status="Running", last_started_at=run["started_at"])
        run_items = [db.create_campaign_run_item(run["id"], target["platform"], target["account_id"], target["target_id"], campaign["post_id"]) for target in targets]
        target_items = list(zip(targets, run_items))
        counters = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        self._running = True

        try:
            self._emit(progress_callback, run, campaign, "Starting campaign", counters)

            for index, (target, item) in enumerate(target_items):
                if item.get("status") != "Pending":
                    continue

                if self.stop_event.is_set():
                    self._mark_remaining_stopped(target_items[index:], counters)
                    return self._finish(run["id"], campaign["id"], "Stopped", counters, "Campaign stopped.", progress_callback)

                result = self._publish_target(campaign, target, item, progress_callback)
                status = result["status"]
                counters["processed"] += 1

                if status == "Success":
                    counters["success"] += 1
                elif status in ("Stopped", "Skipped"):
                    counters["skipped"] += 1
                else:
                    counters["failed"] += 1

                self._update_run(run["id"], counters)
                self._emit(progress_callback, db.get_campaign_run(run["id"]), campaign, "Target finished", counters, target=target)

                if status == "RateLimited" and target["platform"] == "facebook":
                    remaining = target_items[index + 1 :]
                    continue_other = bool(
                        campaign.get("continue_other_platforms_after_facebook_rate_limit")
                    )
                    self._emit(
                        progress_callback,
                        db.get_campaign_run(run["id"]),
                        campaign,
                        "Facebook rate limit",
                        counters,
                        target=target,
                        detection_time=result.get("detection_time") or self._now(),
                    )

                    if continue_other:
                        self._mark_remaining_facebook_stopped(remaining, counters)
                        self._update_run(run["id"], counters)
                        continue

                    self._mark_remaining_stopped(remaining, counters)
                    return self._finish(
                        run["id"],
                        campaign["id"],
                        "Stopped",
                        counters,
                        "Campaign stopped after Facebook rate limit.",
                        progress_callback,
                    )

                should_stop = self.stop_event.is_set() or (
                    status in self.FAILURE_STATUSES and campaign.get("stop_on_error")
                ) or (
                    status == "Checkpoint" and campaign.get("stop_on_checkpoint")
                )

                if should_stop:
                    self._mark_remaining_stopped(target_items[index + 1 :], counters)
                    return self._finish(run["id"], campaign["id"], "Stopped", counters, "Campaign stopped after current target.", progress_callback)

                if index < len(target_items) - 1:
                    self._delay(campaign, progress_callback, run["id"], counters)

            final_status = "CompletedWithErrors" if counters["failed"] else "Completed"
            return self._finish(run["id"], campaign["id"], final_status, counters, "Campaign finished.", progress_callback)
        except Exception as error:
            return self._finish(run["id"], campaign["id"], "Failed", counters, str(error), progress_callback)
        finally:
            self._running = False

    def _publish_target(self, campaign, target, item, progress_callback):
        db.update_campaign_run_item(item["id"], status="Running", started_at=self._now(), message="Publishing.")
        self._emit(progress_callback, None, campaign, "Publishing", {}, target=target)
        adapter = platform_registry.get(target["platform"])
        request = PublishRequest(
            platform=target["platform"],
            account_id=target["account_id"],
            post_id=campaign["post_id"],
            target_ids=[target["target_id"]],
            delay_min=0,
            delay_max=0,
            dry_run=False,
            options={
                "campaign_id": campaign["id"],
                "stop_on_checkpoint": bool(campaign.get("stop_on_checkpoint")),
                "stop_on_block": True,
                "platform_override": self._platform_override(campaign["post_id"], target["platform"]),
                "telegram_parse_mode": None,
            },
        )
        result = adapter.publish(request, progress_callback=None, stop_event=self.stop_event)
        normalized = self._normalize_result(result, target, campaign)
        db.update_campaign_run_item(
            item["id"],
            status=normalized["status"],
            message=normalized["message"],
            publish_history_id=normalized.get("publish_history_id"),
            finished_at=self._now(),
        )
        return normalized

    def _ordered_targets(self, campaign_id):
        rows = db.get_campaign_targets(campaign_id)
        targets = []

        for row in rows:
            target = dict(row)
            target["target_name"] = self._target_name(target)
            targets.append(target)

        return sorted(targets, key=lambda item: (item["platform"], int(item["account_id"]), item["target_name"].lower()))

    def _target_name(self, target):
        if target["platform"] == "facebook":
            row = db.conn.execute("SELECT name FROM groups WHERE id=?", (target["target_id"],)).fetchone()
            return row["name"] if row else f"Target {target['target_id']}"

        if target["platform"] == "telegram":
            row = db.get_telegram_target(target["target_id"])
            if row:
                return row.get("name") or row.get("username") or row.get("external_id") or f"Target {target['target_id']}"

        return f"Target {target['target_id']}"

    def _normalize_result(self, result, target, campaign):
        data = (result or {}).get("data") or {}
        results = data.get("results") or []

        if results:
            item = results[0]
            metadata = item.get("metadata") or item.get("data") or {}
            message = item.get("message") or (result or {}).get("message") or ""
            return {
                "status": item.get("status") or ("Success" if (result or {}).get("success") else "Failed"),
                "message": self._rate_limited_message(message, metadata),
                "publish_history_id": metadata.get("publish_history_id") or self._latest_history_id(campaign, target),
                "detection_time": metadata.get("detection_time") or "",
            }

        status = "Success" if (result or {}).get("success") else "Failed"
        return {
            "status": status,
            "message": (result or {}).get("message") or "",
            "publish_history_id": self._latest_history_id(campaign, target),
        }

    def _latest_history_id(self, campaign, target):
        row = db.conn.execute(
            """
            SELECT id
            FROM publish_history
            WHERE campaign_id=?
              AND platform=?
              AND account_id=?
              AND group_id=?
              AND post_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                campaign["id"],
                target["platform"],
                target["account_id"],
                target["target_id"],
                campaign["post_id"],
            ),
        ).fetchone()
        return row["id"] if row else None

    def _mark_remaining_stopped(self, target_items, counters):
        for _target, item in target_items:
            if item.get("status") != "Pending":
                continue

            db.update_campaign_run_item(item["id"], status="Stopped", message="Campaign stopped.", finished_at=self._now())
            item["status"] = "Stopped"
            counters["skipped"] += 1

    def _mark_remaining_facebook_stopped(self, target_items, counters):
        for target, item in target_items:
            if target["platform"] != "facebook" or item.get("status") != "Pending":
                continue

            db.update_campaign_run_item(
                item["id"],
                status="Stopped",
                message="Stopped because Facebook rate-limited an account in this campaign.",
                finished_at=self._now(),
            )
            item["status"] = "Stopped"
            counters["skipped"] += 1

    def _delay(self, campaign, progress_callback, run_id, counters):
        delay_min = int(campaign.get("delay_min_seconds") or 0)
        delay_max = int(campaign.get("delay_max_seconds") or 0)
        seconds = random.randint(delay_min, delay_max) if delay_max > 0 else 0

        for remaining in range(seconds, 0, -1):
            if self.stop_event.is_set():
                return

            self._emit(
                progress_callback,
                db.get_campaign_run(run_id),
                campaign,
                "Delay",
                counters,
                delay_remaining=remaining,
            )
            time.sleep(1)

    def _finish(self, run_id, campaign_id, status, counters, message, progress_callback):
        run = db.update_campaign_run(
            run_id,
            status=status,
            processed_targets=counters["processed"],
            success_count=counters["success"],
            failed_count=counters["failed"],
            skipped_count=counters["skipped"],
            finished_at=self._now(),
            message=message,
        )
        db.update_campaign(campaign_id, status=status, last_finished_at=run["finished_at"])
        self._emit(progress_callback, run, db.get_campaign(campaign_id), message, counters)
        return {"success": status in ("Completed", "CompletedWithErrors", "Stopped"), "run": run, "message": message}

    def _update_run(self, run_id, counters):
        db.update_campaign_run(
            run_id,
            processed_targets=counters["processed"],
            success_count=counters["success"],
            failed_count=counters["failed"],
            skipped_count=counters["skipped"],
        )

    def _emit(
        self,
        progress_callback,
        run,
        campaign,
        operation,
        counters,
        target=None,
        delay_remaining=0,
        detection_time="",
    ):
        if not progress_callback:
            return

        progress_callback(
            {
                "campaign_id": campaign["id"] if campaign else self.campaign_id,
                "campaign_name": campaign.get("name") if campaign else "",
                "run": run,
                "operation": operation,
                "platform": target.get("platform") if target else "",
                "account_id": target.get("account_id") if target else "",
                "target_id": target.get("target_id") if target else "",
                "target_name": target.get("target_name") if target else "",
                "processed": counters.get("processed", 0),
                "success": counters.get("success", 0),
                "failed": counters.get("failed", 0),
                "skipped": counters.get("skipped", 0),
                "delay_remaining": delay_remaining,
                "detection_time": detection_time,
            }
        )

    def _platform_override(self, post_id, platform):
        post = db.get_post(post_id)

        if not post:
            return {}

        try:
            overrides = json.loads(post.get("platform_overrides") or "{}")
        except json.JSONDecodeError:
            return {}

        return overrides.get(platform) or {}

    def _rate_limited_message(self, message, metadata):
        retry_after = metadata.get("retry_after")

        if retry_after is None:
            return message

        return f"{message} retry_after={retry_after}".strip()

    def _now(self):
        return db.conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
