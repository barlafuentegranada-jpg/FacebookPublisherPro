import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.publisher.engine import PublisherEngine
from app.publisher.navigator import GroupNavigator
from app.publisher.rate_limit_detector import FacebookRateLimitDetector, MockRateLimitDetector
from app.publisher.result import PublishRequest
from app.models.campaign import Campaign
from app.services.accounts_service import AccountsService
from app.services.campaigns_service import CampaignsService
from app.services.publish_service import PublishService
from app.ui.pages.publish_page import PublishPage
from app.workers.campaign_worker import CampaignWorker


class FakeKeyboard:
    def press(self, _key):
        return None


class FakePage:
    def __init__(self):
        self.url = "https://www.facebook.com/groups/test"
        self.keyboard = FakeKeyboard()

    def is_closed(self):
        return False

    def wait_for_timeout(self, _milliseconds):
        return None

    def screenshot(self, **_kwargs):
        return None


class FakeBody:
    def __init__(self, visible=True):
        self.visible = visible

    def wait_for(self, **_kwargs):
        return None

    def is_visible(self, **_kwargs):
        return self.visible

    def inner_text(self, **_kwargs):
        return "Group feed"


class RetryNavigationPage(FakePage):
    def __init__(self, group_url):
        super().__init__()
        self.url = group_url
        self.goto_calls = 0
        self.reload_calls = 0

    def goto(self, url, **_kwargs):
        self.goto_calls += 1
        self.url = url
        raise PlaywrightTimeoutError("navigation timeout")

    def reload(self, **_kwargs):
        self.reload_calls += 1

    def locator(self, selector):
        if selector == "body":
            return FakeBody(visible=self.reload_calls > 0)
        raise AssertionError(f"Unexpected selector: {selector}")


class FakeEditor:
    def __init__(self, identifier):
        self.identifier = identifier


class FakeDialog:
    def __init__(self, page, editor):
        self.page = page
        self.editor = editor
        self.visible = True

    def is_visible(self, timeout=None):
        return self.visible


class FakeNavigator:
    def open_group(self, page, group, on_attempt=None):
        if on_attempt:
            on_attempt(1)
        page.url = group["url"]
        return "Ready", "Group opened."

    def detect_page_state(self, _page):
        return "Ready", "Group opened."


class FakeComposer:
    def __init__(self, insertion_success=True):
        self.insertion_success = insertion_success
        self.opened_editors = []
        self.last_failure_message = ""
        self.last_candidates = []
        self.last_chosen = ""

    def open(self, page):
        editor = FakeEditor(len(self.opened_editors) + 1)
        self.opened_editors.append(editor)
        return FakeDialog(page, editor), editor

    def fill_text(self, _page, _dialog, _editor, _text, worker_thread_id=None):
        if not self.insertion_success:
            self.last_failure_message = "Composer content was not inserted"
        return self.insertion_success

    def insertion_summary(self, _editor):
        return {
            "after_text_length": 24 if self.insertion_success else 0,
            "insertion_method": "keyboard_insert_text",
        }

    def verify_inserted(self, _editor, _text):
        return self.insertion_success

    def visible_dialog(self, _page):
        return None

    def editor(self, dialog):
        return dialog.editor if dialog else None

    def _log(self, _message):
        return None


class FakeUploader:
    def validate_media(self, _post):
        return True, "Media valid."

    def upload(self, _dialog, _post):
        return True, "Media uploaded."


class FakeSubmitter:
    def __init__(self):
        self.last_button = None
        self.last_candidates = []
        self.last_chosen = {}
        self.click_count = 0
        self.calls = 0

    def submit(self, _dialog, _has_payload, upload_complete=True, content_still_present=True):
        self.calls += 1
        self.click_count += 1
        self.last_button = object()
        return True, "Publish clicked.", {"strategy": "test"}


class FakeVerifier:
    def __init__(self, verified=True):
        self.verified = verified

    def verify(self, page, _dialog, _final_text, submit_button=None):
        if self.verified:
            return True, "Verified by test evidence.", page.url, ["dialog closed", "matching feed post"]
        return False, "Publication evidence was not found.", "", []


class TestEngine(PublisherEngine):
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sequence_records = []
        self.rate_limit_records = []

    def _prepare_page(self, _page):
        self._clear_group_references()

    def _open_composer(self, page):
        dialog, editor = self.composer.open(page)
        self._trace["composer_trigger_found"] = bool(dialog)
        self._trace["dialog_found"] = bool(dialog)
        self._trace["editor_found"] = bool(editor)
        return dialog, editor

    def _delay(self, _request, _stop_event, _progress):
        return None

    def _countdown(self, _seconds, _stop_event, _progress, _reason):
        return None

    def _write_sequence_log(self):
        self.sequence_records.append(dict(self._trace))

    def _write_rate_limit_log(self, details):
        self.rate_limit_records.append(dict(details))

    def _close_dialog(self, dialog):
        if dialog:
            dialog.visible = False

    def _log(self, _message):
        return None

    def _log_error(self, _group, _error):
        return None


class PublisherEngineStabilityTests(unittest.TestCase):
    def _engine(
        self,
        insertion_success=True,
        verified=True,
        rate_limit_stage=None,
        on_rate_limited=None,
    ):
        page = FakePage()
        engine = TestEngine(
            page_recovery=lambda: page,
            current_account_id=lambda: 7,
            page_generation=lambda: 3,
            rate_limit_detector=(
                MockRateLimitDetector(detection_stage=rate_limit_stage)
                if rate_limit_stage
                else None
            ),
            on_rate_limited=on_rate_limited,
        )
        engine.navigator = FakeNavigator()
        engine.composer = FakeComposer(insertion_success=insertion_success)
        engine.uploader = FakeUploader()
        engine.submitter = FakeSubmitter()
        engine.verifier = FakeVerifier(verified=verified)
        return engine, page

    def _request(self, group_count):
        return PublishRequest(
            account_id=7,
            post_id=1,
            group_ids=list(range(1, group_count + 1)),
            delay_min_seconds=0,
            delay_max_seconds=0,
            debug_one_group=False,
            stop_after_consecutive_failures=5,
        )

    def _groups(self, group_count):
        return [
            {
                "id": index,
                "name": f"Group {index}",
                "url": f"https://www.facebook.com/groups/{index}",
                "account_id": 7,
            }
            for index in range(1, group_count + 1)
        ]

    def test_staged_runs_reacquire_composer_for_every_group(self):
        for group_count in (3, 8, 15):
            with self.subTest(group_count=group_count):
                engine, page = self._engine()
                result = engine.run(
                    page,
                    self._request(group_count),
                    {"content": "Regression test content"},
                    self._groups(group_count),
                )
                self.assertEqual(result["success_count"], group_count)
                self.assertEqual(result["failure_count"], 0)
                self.assertEqual(len(engine.composer.opened_editors), group_count)
                self.assertEqual(
                    len({id(editor) for editor in engine.composer.opened_editors}),
                    group_count,
                )

    def test_verification_evidence_is_required_for_success(self):
        engine, page = self._engine(verified=False)
        result = engine.run(
            page,
            self._request(1),
            {"content": "Needs publication evidence"},
            self._groups(1),
        )
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["results"][0]["status"], "Failed")

    def test_empty_insertion_never_reaches_submit(self):
        engine, page = self._engine(insertion_success=False)
        result = engine.run(
            page,
            self._request(1),
            {"content": "Must not become empty"},
            self._groups(1),
        )
        self.assertEqual(result["results"][0]["status"], "Failed")
        self.assertEqual(
            result["results"][0]["message"],
            "Composer opened but content insertion failed",
        )
        self.assertEqual(engine.submitter.calls, 0)

    def test_navigation_timeout_reloads_once_then_continues(self):
        group = self._groups(1)[0]
        page = RetryNavigationPage(group["url"])
        state, _message = GroupNavigator().open_group(page, group)
        self.assertEqual(state, "Ready")
        self.assertEqual(page.goto_calls, 1)
        self.assertEqual(page.reload_calls, 1)

    def test_five_technical_failures_stop_the_run(self):
        engine, page = self._engine(insertion_success=False)
        events = []
        result = engine.run(
            page,
            self._request(8),
            {"content": "Must fail safely"},
            self._groups(8),
            progress=events.append,
        )
        self.assertEqual(len(result["results"]), 5)
        self.assertTrue(
            any(
                event.get("event") == "stopped"
                and event.get("data", {}).get("message")
                == "Publishing stopped after repeated Facebook failures"
                for event in events
            )
        )

    def test_rate_limit_detected_at_every_required_stage(self):
        stages = [
            "after_navigation",
            "after_composer_open",
            "after_content_insertion",
            "after_submit_click",
            "after_verification",
        ]

        for stage in stages:
            with self.subTest(stage=stage):
                account_events = []
                engine, page = self._engine(
                    rate_limit_stage=stage,
                    on_rate_limited=account_events.append,
                )
                result = engine.run(
                    page,
                    self._request(1),
                    {"content": "Mocked local rate-limit test"},
                    self._groups(1),
                )
                self.assertEqual(result["results"][0]["status"], "RateLimited")
                self.assertEqual(result["success_count"], 0)
                self.assertEqual(account_events[0]["detection_stage"], stage)
                self.assertEqual(
                    engine.rate_limit_records[0]["matched_phrase_key"],
                    "limit_post_frequency",
                )

    def test_rate_limit_stops_run_and_marks_remaining_history(self):
        account_events = []
        progress_events = []
        history_state = {}

        def history(group_id, status, message="", **_kwargs):
            history_state[group_id] = {"status": status, "message": message}

        engine, page = self._engine(
            rate_limit_stage="after_composer_open",
            on_rate_limited=account_events.append,
        )
        result = engine.run(
            page,
            self._request(3),
            {"content": "Mocked local rate-limit test"},
            self._groups(3),
            progress=progress_events.append,
            history=history,
        )
        self.assertEqual(
            [item["status"] for item in result["results"]],
            ["RateLimited", "Stopped", "Stopped"],
        )
        self.assertEqual(history_state[1]["status"], "RateLimited")
        self.assertEqual(history_state[2]["status"], "Stopped")
        self.assertEqual(history_state[3]["status"], "Stopped")
        self.assertEqual(len(account_events), 1)
        warning = next(event for event in progress_events if event["event"] == "rate_limited")
        self.assertEqual(warning["data"]["completed_count"], 1)
        self.assertEqual(warning["data"]["remaining_count"], 2)


class VisibleLocator:
    def __init__(self, visible):
        self.visible = visible

    def count(self):
        return int(self.visible)

    def nth(self, _index):
        return self

    def is_visible(self, timeout=None):
        return self.visible


class VisibleTextScope:
    def __init__(self, visible_phrase):
        self.visible_phrase = visible_phrase

    def get_by_text(self, phrase, exact=False):
        return VisibleLocator(phrase == self.visible_phrase)

    def get_by_role(self, _role, name=None, exact=False):
        return VisibleLocator(name == self.visible_phrase)


class AccountStateDb:
    def __init__(self, accounts):
        self.accounts = accounts

    def set_account_publishing_state(self, account_id, publishing_state, updated_at=None):
        self.accounts[account_id]["publishing_state"] = publishing_state
        self.accounts[account_id]["publishing_state_updated_at"] = updated_at or "now"


class AccountStateService(AccountsService):
    def __init__(self, accounts):
        self.accounts = accounts

    def get_account(self, account_id):
        account = self.accounts.get(account_id)
        return dict(account) if account else None


class CampaignPolicyDb:
    def __init__(self):
        self.updated = []

    def update_campaign_run_item(self, item_id, **fields):
        self.updated.append((item_id, fields))


class RateLimitPolicyTests(unittest.TestCase):
    def test_visible_arabic_phrase_is_sanitized_to_key(self):
        phrase = "يمكنك المحاولة مرة أخرى لاحقًا"
        result = FacebookRateLimitDetector().detect(
            VisibleTextScope(phrase),
            stage="after_navigation",
        )
        self.assertEqual(result["matched_key"], "try_again_later")
        self.assertNotIn(phrase, result.values())

    def test_account_requires_confirmation_before_available(self):
        accounts = {
            7: {
                "id": 7,
                "platform": "facebook",
                "publishing_state": "Available",
            }
        }
        fake_db = AccountStateDb(accounts)
        service = AccountStateService(accounts)

        with patch("app.services.accounts_service.db", fake_db):
            service.mark_rate_limited(7, detection_time="2026-07-23T12:00:00")
            self.assertEqual(accounts[7]["publishing_state"], "RateLimited")
            with self.assertRaises(ValueError):
                service.mark_available_after_review(7, confirmed=False)
            service.mark_available_after_review(7, confirmed=True)
            self.assertEqual(accounts[7]["publishing_state"], "Available")

    def test_publish_and_campaign_availability_are_facebook_only(self):
        facebook = {
            "platform": "facebook",
            "status": "Logged in",
            "publishing_state": "RateLimited",
        }
        telegram = {
            "platform": "telegram",
            "status": "Connected",
            "publishing_state": "RateLimited",
        }
        service = CampaignsService()
        self.assertFalse(service._account_connected(facebook))
        self.assertTrue(service._account_connected(telegram))
        self.assertFalse(PublishPage._facebook_publishing_available(facebook))

    def test_continue_policy_stops_facebook_but_leaves_telegram_pending(self):
        fake_db = CampaignPolicyDb()
        worker = CampaignWorker(1)
        worker._now = lambda: "now"
        targets = [
            ({"platform": "facebook"}, {"id": 1, "status": "Pending"}),
            ({"platform": "facebook"}, {"id": 2, "status": "Pending"}),
            ({"platform": "telegram"}, {"id": 3, "status": "Pending"}),
        ]
        counters = {"skipped": 0}

        with patch("app.workers.campaign_worker.db", fake_db):
            worker._mark_remaining_facebook_stopped(targets, counters)

        self.assertEqual(targets[0][1]["status"], "Stopped")
        self.assertEqual(targets[1][1]["status"], "Stopped")
        self.assertEqual(targets[2][1]["status"], "Pending")
        self.assertEqual(counters["skipped"], 2)
        self.assertFalse(Campaign().continue_other_platforms_after_facebook_rate_limit)

    def test_default_campaign_policy_stops_facebook_and_telegram(self):
        fake_db = CampaignPolicyDb()
        worker = CampaignWorker(1)
        worker._now = lambda: "now"
        targets = [
            ({"platform": "facebook"}, {"id": 1, "status": "Pending"}),
            ({"platform": "telegram"}, {"id": 2, "status": "Pending"}),
        ]
        counters = {"skipped": 0}

        with patch("app.workers.campaign_worker.db", fake_db):
            worker._mark_remaining_stopped(targets, counters)

        self.assertEqual([item["status"] for _target, item in targets], ["Stopped", "Stopped"])
        self.assertEqual(counters["skipped"], 2)

    def test_rate_limit_log_contains_only_sanitized_fields(self):
        engine = TestEngine()

        with tempfile.TemporaryDirectory() as temp_dir:
            engine.rate_limit_log_path = Path(temp_dir) / "rate_limit.log"
            PublisherEngine._write_rate_limit_log(
                engine,
                {
                    "detection_time": "2026-07-23T12:00:00",
                    "account_id": 7,
                    "group_id": 11,
                    "run_id": "run-1",
                    "detection_stage": "after_submit_click",
                    "matched_phrase_key": "limit_post_frequency",
                    "private_text": "must not be written",
                },
            )
            record = json.loads(engine.rate_limit_log_path.read_text(encoding="utf-8"))

        self.assertEqual(
            set(record),
            {
                "timestamp",
                "account_id",
                "group_id",
                "run_id",
                "detection_stage",
                "matched_phrase_key",
                "action_taken",
            },
        )
        self.assertNotIn("private_text", record)

    def test_wrapper_failure_does_not_overwrite_rate_limited_history(self):
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE publish_history (id INTEGER PRIMARY KEY, status TEXT, message TEXT, finished_at TEXT)"
        )
        connection.executemany(
            "INSERT INTO publish_history (id, status) VALUES (?, ?)",
            [(1, "RateLimited"), (2, "Pending")],
        )

        class HistoryDb:
            conn = connection

            def update_publish_history(self, history_id, **fields):
                self.conn.execute(
                    "UPDATE publish_history SET status=?, message=?, finished_at=? WHERE id=?",
                    (
                        fields.get("status"),
                        fields.get("message"),
                        fields.get("finished_at"),
                        history_id,
                    ),
                )

        service = PublishService()
        service._now = lambda: "now"

        with patch("app.services.publish_service.db", HistoryDb()):
            service._fail_pending_history({11: 1, 12: 2}, 11, "wrapper failure")
            service._fail_pending_history({11: 1, 12: 2}, 12, "wrapper failure")

        statuses = [
            row[0]
            for row in connection.execute(
                "SELECT status FROM publish_history ORDER BY id"
            ).fetchall()
        ]
        connection.close()
        self.assertEqual(statuses, ["RateLimited", "Failed"])


if __name__ == "__main__":
    unittest.main()
