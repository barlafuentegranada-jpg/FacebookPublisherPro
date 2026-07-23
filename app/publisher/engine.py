import json
import random
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from app.publisher.composer import Composer
from app.publisher.media_uploader import MediaUploader
from app.publisher.navigator import GroupNavigator
from app.publisher.rate_limit_detector import FacebookRateLimitDetector
from app.publisher.result import PublishResult
from app.publisher.submitter import Submitter
from app.publisher.verifier import Verifier


class PublisherEngine:
    TERMINAL_STATUSES = {
        "Success",
        "Failed",
        "PermissionDenied",
        "Blocked",
        "Checkpoint",
        "RateLimited",
        "Stopped",
        "Validated",
        "ValidationFailed",
    }

    RATE_LIMIT_MESSAGE = (
        "Facebook temporarily limited posting for this account. "
        "Publishing has been stopped. Review Facebook Account Status and "
        "Support Inbox before trying again."
    )

    def __init__(
        self,
        page_recovery=None,
        current_account_id=None,
        page_generation=None,
        rate_limit_detector=None,
        on_rate_limited=None,
    ):
        self.navigator = GroupNavigator()
        self.composer = Composer()
        self.uploader = MediaUploader()
        self.submitter = Submitter()
        self.verifier = Verifier()
        self.rate_limit_detector = rate_limit_detector or FacebookRateLimitDetector()
        self.log_path = Path("logs/publisher.log")
        self.page_recovery = page_recovery
        self.current_account_id = current_account_id
        self.page_generation = page_generation
        self.on_rate_limited = on_rate_limited
        self.sequence_log_path = Path("logs/publish_sequence.log")
        self.rate_limit_log_path = Path("logs/rate_limit.log")
        self._trace = {}

    def run(self, page, request, post, groups, stop_event=None, progress=None, history=None, worker_thread_id=None):
        results = []
        self._current_page = page
        target_groups = groups[:1] if request.debug_one_group else groups
        run_id = uuid.uuid4().hex
        consecutive_failures = 0
        consecutive_technical_failures = 0
        failure_limit = max(1, int(getattr(request, "stop_after_consecutive_failures", 5) or 5))

        for index, group in enumerate(target_groups):
            if self._stopped(stop_event):
                break

            result = PublishResult(
                group_id=group["id"],
                group_name=group["name"],
                group_url=group["url"],
            )

            if group.get("account_id") != request.account_id or self._active_account_changed(request.account_id):
                final = result.finish("Stopped", "Active account changed during publishing.")
                self._history(history, group, final.status, final.message, finished_at=final.finished_at)
                results.append(final.to_dict())
                self._emit(progress, "result", final.to_dict())
                break

            self._trace = self._new_trace(
                run_id,
                index + 1,
                group,
                consecutive_failures,
            )
            started = time.monotonic()
            self._emit(
                progress,
                "group_progress",
                {
                    "current": index + 1,
                    "total": len(target_groups),
                    "consecutive_failures": consecutive_failures,
                },
            )

            try:
                page = self._recover_page()
                self._transition(history, group, "Preparing", "Preparing group page.")
                self._prepare_page(page)
                final = self._publish_group(
                    page,
                    request,
                    post,
                    group,
                    result,
                    progress,
                    history,
                    worker_thread_id,
                    stop_event,
                )
            except Exception as error:
                self._log_error(group, error)
                final = result.finish("Failed", str(error))
                self._trace["failure_stage"] = self._trace.get("state") or "unknown"
                self._history(history, group, "Failed", final.message, finished_at=final.finished_at)

            if final.status not in self.TERMINAL_STATUSES:
                final = result.finish("Failed", f"Non-terminal publishing state: {final.status}")
                self._history(history, group, final.status, final.message, finished_at=final.finished_at)

            failed = final.status in {
                "Failed",
                "PermissionDenied",
                "Blocked",
                "Checkpoint",
                "ValidationFailed",
            }
            technical_failure = final.status == "Failed" and self._trace.get("failure_stage") in {
                "Navigating",
                "OpeningComposer",
                "ComposerOpened",
                "InsertingContent",
                "ContentVerified",
                "ReadyToSubmit",
                "Submitting",
                "Verifying",
            }
            consecutive_failures = consecutive_failures + 1 if failed else 0
            consecutive_technical_failures = consecutive_technical_failures + 1 if technical_failure else 0
            self._trace.update(
                {
                    "terminal_status": final.status,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "consecutive_failures": consecutive_failures,
                }
            )
            self._write_sequence_log()
            results.append(final.to_dict())
            self._emit(progress, "result", final.to_dict())
            self._emit(
                progress,
                "group_progress",
                {
                    "current": index + 1,
                    "total": len(target_groups),
                    "consecutive_failures": consecutive_failures,
                },
            )

            if final.status == "RateLimited":
                remaining_groups = target_groups[index + 1 :]
                stopped_results = self._stop_remaining_groups(
                    remaining_groups,
                    history,
                    progress,
                    run_id,
                    index + 2,
                )
                results.extend(stopped_results)
                detection_time = final.data.get("detection_time") or datetime.now().isoformat(timespec="seconds")
                self._emit(
                    progress,
                    "rate_limited",
                    {
                        "message": self.RATE_LIMIT_MESSAGE,
                        "account_id": request.account_id,
                        "detection_time": detection_time,
                        "current_group": group.get("name") or "",
                        "completed_count": index + 1,
                        "remaining_count": len(remaining_groups),
                    },
                )
                break

            if final.status == "Checkpoint" and request.stop_on_checkpoint:
                self._emit(progress, "stopped", {"message": "Stopped on checkpoint."})
                break

            if final.status == "Blocked" and request.stop_on_block:
                self._emit(progress, "stopped", {"message": "Stopped on block."})
                break

            if consecutive_technical_failures >= 5:
                self._emit(
                    progress,
                    "stopped",
                    {"message": "Publishing stopped after repeated Facebook failures"},
                )
                break

            if consecutive_failures >= failure_limit:
                self._emit(
                    progress,
                    "stopped",
                    {"message": f"Stopped after {consecutive_failures} consecutive failures."},
                )
                break

            if index < len(target_groups) - 1 and not request.debug_one_group:
                if consecutive_failures >= 3:
                    self._countdown(30, stop_event, progress, "cooldown")
                elif failed:
                    self._countdown(5, stop_event, progress, "stabilization")
                else:
                    self._delay(request, stop_event, progress)

        return {
            "results": results,
            "success_count": sum(1 for item in results if item["status"] == "Success"),
            "failure_count": sum(
                1
                for item in results
                if item["status"] in ["Failed", "PermissionDenied", "Checkpoint", "Blocked", "RateLimited", "ValidationFailed"]
            ),
            "skipped_count": sum(1 for item in results if item["status"] in ["Skipped", "Stopped"]),
        }

    def _publish_group(self, page, request, post, group, result, progress, history, worker_thread_id=None, stop_event=None):
        self._emit(progress, "current", {"group": group["name"], "operation": "Navigating"})
        self._transition(history, group, "Navigating", "Opening group.")
        state, message = self.navigator.open_group(
            page,
            group,
            on_attempt=lambda attempt: self._trace.__setitem__("navigation_attempt", attempt),
        )
        self._trace["final_url"] = self._safe_url(page)
        rate_limited = self._rate_limit_result(
            page,
            None,
            "after_navigation",
            request,
            group,
            result,
            history,
        )

        if rate_limited:
            return rate_limited

        if state == "LoginRequired":
            final = result.finish("Failed", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if state == "TwoFactor":
            final = result.finish("Checkpoint", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if state == "Checkpoint":
            final = result.finish("Checkpoint", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if state == "Unavailable":
            final = result.finish("Failed", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if state == "Blocked":
            final = result.finish("Blocked", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if state == "PermissionDenied":
            final = result.finish("PermissionDenied", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if state == "Failed":
            self._trace["failure_stage"] = "Navigating"
            self._screenshot(page, group, "navigation_timeout")
            final = result.finish("Failed", message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        self._transition(history, group, "PageReady", message)
        self._emit(progress, "current", {"group": group["name"], "operation": "Composing"})
        self._transition(history, group, "OpeningComposer", "Opening composer.")
        dialog, editor = self._open_composer(page)
        rate_limited = self._rate_limit_result(
            page,
            dialog,
            "after_composer_open",
            request,
            group,
            result,
            history,
        )

        if rate_limited:
            return rate_limited

        if not dialog:
            detected_state, detected_message = self.navigator.detect_page_state(page)

            if detected_state in {"PermissionDenied", "Blocked", "Checkpoint"}:
                final = result.finish(detected_state, detected_message)
                self._history(history, group, final.status, final.message, finished_at=final.finished_at)
                return final

            self._trace["failure_stage"] = "OpeningComposer"
            trigger_found = self._trace.get("composer_trigger_found")
            screenshot_reason = "dialog_not_found" if trigger_found else "composer_trigger_not_found"
            failure_message = (
                "Post composer dialog did not open."
                if trigger_found
                else "Post composer trigger was not found."
            )
            self._screenshot(page, group, screenshot_reason)
            final = result.finish("Failed", failure_message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        self._trace["dialog_found"] = True
        self._transition(history, group, "ComposerOpened", "Composer dialog opened.")

        if not editor:
            self._close_dialog(dialog)
            dialog, editor = self._open_composer(page)

            if not editor:
                self._trace["failure_stage"] = "ComposerOpened"
                self._screenshot(page, group, "editor_not_found")
                self._close_dialog(dialog)
                final = result.finish("Failed", "Composer dialog opened but its editor was not found.")
                self._history(history, group, final.status, final.message, finished_at=final.finished_at)
                return final

        self._trace["editor_found"] = True

        media_ok, media_message = self.uploader.validate_media(post)

        if not media_ok:
            final = result.finish("ValidationFailed", media_message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        final_text = self._final_text(post)
        self._trace["final_text_length"] = len(final_text)
        self.composer._log(f"final_text_length={len(final_text)}")

        if not final_text:
            final = result.finish("Failed", "Post content is empty")
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        self._transition(history, group, "InsertingContent", "Inserting composer content.")
        inserted = False
        composer_status = ""
        composer_message = ""

        for insertion_attempt in (1, 2):
            if insertion_attempt == 2:
                dialog = self.composer.visible_dialog(page)
                editor = self.composer.editor(dialog) if dialog else None

                if not editor:
                    break

            self.composer._log("composer_insert:engine_call_before")
            composer_result = self.composer.fill_text(
                page,
                dialog,
                editor,
                final_text,
                worker_thread_id=worker_thread_id,
            )
            self.composer._log("composer_insert:engine_call_after")
            inserted, composer_status, composer_message = self._composer_result_fields(composer_result)

            if inserted:
                break

        self._log(
            f"engine:composer_result success={inserted} "
            f"status={composer_status} message={composer_message}"
        )
        rate_limited = self._rate_limit_result(
            page,
            dialog,
            "after_content_insertion",
            request,
            group,
            result,
            history,
        )

        if rate_limited:
            return rate_limited

        if not inserted:
            summary = self.composer.insertion_summary(editor) if editor else {}
            self._trace["after_length"] = summary.get("after_text_length", 0)
            self._trace["content_verified"] = False
            self._trace["failure_stage"] = "InsertingContent"
            failure_message = (
                "Composer opened but content insertion failed"
                if len(final_text) > 0 and not summary.get("after_length")
                else self.composer.last_failure_message or "Composer content was not inserted"
            )
            if failure_message == "Composer text insertion timed out":
                self._screenshot(page, group, "content_insert_timeout")
            else:
                self._screenshot(page, group, "content_not_inserted")
            self._close_dialog(dialog)
            final = result.finish("Failed", failure_message)
            final.data = summary
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        insertion_summary = self.composer.insertion_summary(editor)
        self._trace["after_length"] = insertion_summary.get("after_text_length", 0)
        self._trace["content_verified"] = True
        self._transition(history, group, "ContentVerified", "Composer content verified.")

        if request.dry_run or request.composer_debug_only:
            reason = "dry_run" if request.dry_run else "composer_debug_only"
            self._log(f"engine:submit_stage_skipped reason={reason}")
            final = result.finish("Validated", "Content inserted successfully")
            final.data = insertion_summary
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        self._emit(progress, "current", {"group": group["name"], "operation": "Uploading"})
        self._transition(history, group, "UploadingMedia", "Preparing media upload.")
        has_media = bool(post.get("image_path") or post.get("video_path"))
        upload_ok = True
        upload_message = "No media selected."

        if has_media:
            upload_ok, upload_message = self.uploader.upload(dialog, post)

        if has_media and not upload_ok:
            self._log("engine:submit_stage_skipped reason=media_upload_failed")
            final = result.finish("Failed", upload_message)
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            return final

        if has_media:
            self._history(history, group, "MediaUploaded", upload_message)

        self._emit(progress, "current", {"group": group["name"], "operation": "Publishing"})
        has_payload = bool(final_text or post.get("image_path") or post.get("video_path"))
        content_still_present = self.composer.verify_inserted(editor, final_text)
        self._transition(history, group, "ReadyToSubmit", "Composer is ready to submit.")
        self._transition(history, group, "Submitting", "Submitting post.")
        self._log("engine:submit_stage_before")
        submitted, submit_message, submit_details = self.submitter.submit(
            dialog,
            has_payload,
            upload_complete=upload_ok,
            content_still_present=content_still_present,
        )
        self._log("engine:submit_stage_after")
        self._trace["submit_button_found"] = bool(submit_details)
        self._trace["submit_clicked"] = bool(submitted)
        rate_limited = self._rate_limit_result(
            page,
            dialog,
            "after_submit_click",
            request,
            group,
            result,
            history,
        )

        if rate_limited:
            return rate_limited

        if not submitted:
            self._trace["failure_stage"] = "Submitting"
            if submit_message == "Facebook submit button remained disabled":
                self._screenshot(page, group, "submit_not_found")
            else:
                self._screenshot(page, group, "submit_not_found")
            final = result.finish("Failed", submit_message)
            final.data = {
                "insertion": insertion_summary,
                "submit_button": submit_details,
                "submit_candidates": self.submitter.last_candidates,
            }
            self._history(history, group, final.status, final.message, finished_at=final.finished_at)
            self._log(f"engine:terminal_status status={final.status} message={final.message}")
            return final

        self._transition(history, group, "Verifying", "Verifying publication.")
        self._log("engine:verification_stage_before")
        verified, verify_message, published_url, verification_signals = self.verifier.verify(
            page,
            dialog,
            final_text,
            submit_button=self.submitter.last_button,
        )
        self._trace["verification_signals"] = verification_signals
        rate_limited = self._rate_limit_result(
            page,
            dialog,
            "after_verification",
            request,
            group,
            result,
            history,
        )

        if rate_limited:
            return rate_limited

        if verified:
            try:
                page.wait_for_timeout(1500)
            except Exception:
                pass
            final = result.finish("Success", verify_message, published_url)
            final.data = {
                "insertion": insertion_summary,
                "submit_button": submit_details,
                "click_count": self.submitter.click_count,
                "verification_signals": verification_signals,
            }
            self._history(history, group, final.status, final.message, finished_at=final.finished_at, published_post_url=published_url)
            self._log(f"engine:terminal_status status={final.status} message={final.message}")
            return final

        self._screenshot(page, group, "verification_failed")
        self._trace["failure_stage"] = "Verifying"
        final = result.finish("Failed", verify_message)
        final.data = {
            "insertion": insertion_summary,
            "submit_button": submit_details,
            "click_count": self.submitter.click_count,
            "verification_signals": verification_signals,
        }
        self._history(history, group, final.status, final.message, finished_at=final.finished_at)
        self._log(f"engine:terminal_status status={final.status} message={final.message}")
        return final

    def _recover_page(self):
        if self.page_recovery:
            self._current_page = self.page_recovery()

        page = getattr(self, "_current_page", None)

        if page is None or page.is_closed():
            raise RuntimeError("Facebook page is not available.")

        return page

    def _prepare_page(self, page):
        self._clear_group_references()

        if page.is_closed():
            raise RuntimeError("Facebook page is closed.")

        if not self._auth_sensitive_page(page):
            dialogs = page.locator("div[role='dialog']")

            for index in range(dialogs.count()):
                dialog = dialogs.nth(index)

                try:
                    if dialog.is_visible(timeout=300) and self.composer.editor(dialog):
                        self._close_dialog(dialog)
                except Exception:
                    continue

            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

    def _clear_group_references(self):
        self.submitter.last_button = None
        self.submitter.last_candidates = []
        self.submitter.last_chosen = {}
        self.submitter.click_count = 0
        self.composer.last_candidates = []
        self.composer.last_chosen = ""

    def _open_composer(self, page):
        trigger_found = False

        for attempt in (1, 2):
            trigger_found = trigger_found or self._composer_trigger_visible(page)

            try:
                dialog, editor = self.composer.open(page)
            except Exception:
                dialog, editor = None, None

            if dialog and not editor:
                self._trace["composer_trigger_found"] = True
                self._trace["dialog_found"] = True
                self._trace["editor_found"] = False
                return dialog, None

            if dialog:
                active = self._active_composer_dialogs(page)

                if len(active) != 1:
                    for stale_dialog, _stale_editor in active:
                        self._close_dialog(stale_dialog)

                    dialog, editor = None, None
                else:
                    dialog, editor = active[0]

            if dialog:
                self._trace["composer_trigger_found"] = True
                self._trace["dialog_found"] = True
                self._trace["editor_found"] = bool(editor)
                return dialog, editor

            if attempt == 1:
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, 0)")

        self._trace["composer_trigger_found"] = trigger_found
        return None, None

    def _active_composer_dialogs(self, page):
        active = []

        try:
            dialogs = page.locator("div[role='dialog']")

            for index in range(dialogs.count()):
                dialog = dialogs.nth(index)

                if not dialog.is_visible(timeout=300):
                    continue

                editor = self.composer.editor(dialog)

                if editor:
                    active.append((dialog, editor))
        except Exception:
            return []

        return active

    def _composer_trigger_visible(self, page):
        for text in self.composer.OPEN_TEXTS:
            try:
                candidates = page.get_by_text(text, exact=False)

                for index in range(candidates.count()):
                    if candidates.nth(index).is_visible(timeout=300):
                        return True
            except Exception:
                continue

        return False

    def _close_dialog(self, dialog):
        if not dialog:
            return

        try:
            if not dialog.is_visible(timeout=500):
                return

            close_buttons = dialog.get_by_role(
                "button",
                name=r"Close|Cancel|إغلاق|إلغاء",
            )

            if close_buttons.count() > 0:
                close_buttons.first.click(timeout=2000)
            else:
                dialog.page.keyboard.press("Escape")

            dialog.page.wait_for_timeout(500)
        except Exception:
            pass

    def _transition(self, history, group, state, message):
        self._trace["state"] = state
        self._history(history, group, state, message)

    def _rate_limit_result(self, page, dialog, stage, request, group, result, history):
        detection = self.rate_limit_detector.detect(page, dialog=dialog, stage=stage)

        if not detection:
            return None

        detection_time = datetime.now().isoformat(timespec="seconds")
        matched_key = detection.get("matched_key") or "unknown"
        self._close_dialog(dialog)
        details = {
            "account_id": request.account_id,
            "group_id": group.get("id"),
            "run_id": self._trace.get("run_id") or "",
            "detection_stage": stage,
            "matched_phrase_key": matched_key,
            "detection_time": detection_time,
        }
        self._trace["failure_stage"] = stage
        self._trace["rate_limit_phrase_key"] = matched_key

        if self.on_rate_limited:
            self.on_rate_limited(details)

        self._write_rate_limit_log(details)
        final = result.finish("RateLimited", self.RATE_LIMIT_MESSAGE)
        final.data = {
            "detection_time": detection_time,
            "detection_stage": stage,
            "matched_phrase_key": matched_key,
        }
        self._history(
            history,
            group,
            final.status,
            final.message,
            finished_at=final.finished_at,
        )
        self._log(f"engine:terminal_status status={final.status} message=facebook_rate_limit")
        return final

    def _write_rate_limit_log(self, details):
        record = {
            "timestamp": details.get("detection_time") or datetime.now().isoformat(timespec="seconds"),
            "account_id": details.get("account_id"),
            "group_id": details.get("group_id"),
            "run_id": details.get("run_id") or "",
            "detection_stage": details.get("detection_stage") or "unknown",
            "matched_phrase_key": details.get("matched_phrase_key") or "unknown",
            "action_taken": "stopped_facebook_run_and_required_manual_review",
        }
        self.rate_limit_log_path.parent.mkdir(parents=True, exist_ok=True)

        with self.rate_limit_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")

    def _stop_remaining_groups(self, groups, history, progress, run_id, start_sequence):
        stopped = []

        for offset, group in enumerate(groups):
            final = PublishResult(
                group_id=group["id"],
                group_name=group["name"],
                group_url=group["url"],
            ).finish(
                "Stopped",
                "Stopped because Facebook temporarily limited posting for this account.",
            )
            self._history(
                history,
                group,
                final.status,
                final.message,
                finished_at=final.finished_at,
            )
            item = final.to_dict()
            stopped.append(item)
            self._emit(progress, "result", item)
            self._trace = self._new_trace(
                run_id,
                start_sequence + offset,
                group,
                0,
            )
            self._trace.update(
                {
                    "terminal_status": "Stopped",
                    "elapsed_seconds": 0,
                }
            )
            self._write_sequence_log()

        return stopped

    def _new_trace(self, run_id, sequence_number, group, consecutive_failures):
        return {
            "run_id": run_id,
            "sequence_number": sequence_number,
            "group_id": group.get("id"),
            "group_name": group.get("name") or "",
            "group_url": self._sanitize_url(group.get("url") or ""),
            "page_generation": self.page_generation() if self.page_generation else 0,
            "navigation_attempt": 0,
            "final_url": "",
            "composer_trigger_found": False,
            "dialog_found": False,
            "editor_found": False,
            "final_text_length": 0,
            "after_length": 0,
            "content_verified": False,
            "submit_button_found": False,
            "submit_clicked": False,
            "verification_signals": [],
            "terminal_status": "",
            "elapsed_seconds": 0,
            "consecutive_failures": consecutive_failures,
        }

    def _write_sequence_log(self):
        allowed = {
            "run_id",
            "sequence_number",
            "group_id",
            "group_name",
            "group_url",
            "page_generation",
            "navigation_attempt",
            "final_url",
            "composer_trigger_found",
            "dialog_found",
            "editor_found",
            "final_text_length",
            "after_length",
            "content_verified",
            "submit_button_found",
            "submit_clicked",
            "verification_signals",
            "terminal_status",
            "elapsed_seconds",
            "consecutive_failures",
        }
        record = {key: self._trace.get(key) for key in allowed}
        self.sequence_log_path.parent.mkdir(parents=True, exist_ok=True)

        with self.sequence_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")

    def _safe_url(self, page):
        try:
            return self._sanitize_url(page.url)
        except Exception:
            return ""

    def _sanitize_url(self, url):
        if "encrypted_context" in str(url):
            return ""

        return str(url).split("?")[0]

    def _countdown(self, seconds, stop_event, progress, reason):
        for remaining in range(seconds, 0, -1):
            if self._stopped(stop_event):
                self._emit(progress, "stopped", {"message": "Stopped during cooldown."})
                return

            self._emit(
                progress,
                "cooldown",
                {"remaining_seconds": remaining, "reason": reason},
            )
            time.sleep(1)

    def _delay(self, request, stop_event, progress):
        seconds = random.randint(request.delay_min_seconds, request.delay_max_seconds)

        for remaining in range(seconds, 0, -1):
            if self._stopped(stop_event):
                self._emit(progress, "stopped", {"message": "Stopped during delay."})
                return

            self._emit(progress, "delay", {"remaining_seconds": remaining})
            time.sleep(1)

    def _final_text(self, post):
        parts = []

        if post.get("content"):
            parts.append(post["content"].strip())

        if post.get("youtube_url"):
            parts.append(post["youtube_url"].strip())

        return "\n\n".join(parts).strip()

    def _stopped(self, stop_event):
        return bool(stop_event and stop_event.is_set())

    def _composer_result_fields(self, composer_result):
        if isinstance(composer_result, dict):
            success = self._first_present(
                composer_result,
                ["success", "verified", "inserted", "ok"],
                default=None,
            )
            status = self._first_present(composer_result, ["status", "state"], default="")
            message = self._first_present(composer_result, ["message", "error"], default="")
            if success is None:
                success = self._status_is_success(status)
            return bool(success), status or "", message or ""

        if isinstance(composer_result, tuple):
            success = composer_result[0] if len(composer_result) > 0 else False
            status = composer_result[1] if len(composer_result) > 1 else ""
            message = composer_result[2] if len(composer_result) > 2 else ""
            return bool(success), status or "", message or ""

        for success_field in ["success", "verified", "inserted", "ok"]:
            if hasattr(composer_result, success_field):
                status = self._first_attr(composer_result, ["status", "state"], default="")
                message = self._first_attr(composer_result, ["message", "error"], default="")
                return bool(getattr(composer_result, success_field)), status or "", message or ""

        status = self._first_attr(composer_result, ["status", "state"], default="")
        message = self._first_attr(composer_result, ["message", "error"], default="")

        if status:
            return self._status_is_success(status), status or "", message or ""

        return bool(composer_result), "", ""

    def _status_is_success(self, status):
        return str(status or "").strip().lower() in {
            "success",
            "succeeded",
            "verified",
            "inserted",
            "ok",
            "complete",
            "completed",
        }

    def _first_present(self, data, keys, default=None):
        for key in keys:
            if key in data:
                return data.get(key)
        return default

    def _first_attr(self, item, names, default=None):
        for name in names:
            if hasattr(item, name):
                return getattr(item, name)
        return default

    def _emit(self, progress, event, data):
        if progress:
            progress(
                {
                    "event": event,
                    "data": data,
                }
            )

    def _history(self, history, group, status, message="", finished_at=None, published_post_url=""):
        if history:
            history(
                group["id"],
                status,
                message,
                finished_at=finished_at,
                published_post_url=published_post_url,
            )

    def _screenshot(self, page, group, step):
        if self._auth_sensitive_page(page):
            return

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        path = Path("logs/screenshots") / f"{timestamp}_{group.get('id')}_{step}.png"
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            page.screenshot(path=str(path), full_page=False)
        except Exception:
            self._log_error(group, RuntimeError(f"Screenshot failed for {step}"))

    def _auth_sensitive_page(self, page):
        try:
            state, _message = self.navigator.detect_page_state(page)
            return state in {"LoginRequired", "TwoFactor", "Checkpoint", "Blocked"}
        except Exception:
            return True

    def _active_account_changed(self, account_id):
        if not self.current_account_id:
            return False

        return self.current_account_id() != account_id

    def _browser_log(self, event, message):
        path = Path("logs/browser.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {event}: {message}\n")

    def _log(self, message):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        text = str(message)

        if "encrypted_context" in text:
            text = "[redacted encrypted context]"

        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text[:3000]}\n")

    def _log_error(self, group, error):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        message = traceback.format_exc()

        if "encrypted_context" in message:
            message = "[redacted encrypted context]"

        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] group={group.get('id')} error={message[:4000]}\n"
            )
