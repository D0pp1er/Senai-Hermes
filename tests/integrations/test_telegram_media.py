import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai.telegram.api import BotAPI, TelegramError
from senai.telegram.media import MediaOutbox

PNG = b"\x89PNG\r\n\x1a\n" + b"fixture"


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "outputs"
        self.state = self.workspace / "state"
        self.outbox = MediaOutbox(self.workspace, self.state)
        self.image = self.workspace / "picture.png"
        self.image.write_bytes(PNG)
        self.manifest = self.state / "jobs/1/attachments.json"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({"images": ["picture.png"]}))
        self.job = {"id": 1, "chat_id": 7, "user_id": 7}
        self.api = Mock()

    def test_selected_image_is_snapshotted_not_resolved_again_on_retry(self):
        self.outbox.prepare(1, self.manifest)
        self.image.write_bytes(b"changed")
        self.outbox.deliver(self.job, self.api, authorized=lambda: True)
        sent = self.api.send_photo.call_args.args
        self.assertEqual(sent[0], 7)
        self.assertEqual(Path(sent[1]).read_bytes(), PNG)
        self.outbox.deliver(self.job, self.api, authorized=lambda: True)
        self.api.send_photo.assert_called_once()

    def test_restart_retries_upload_without_resending_finished_photos(self):
        (self.workspace / "second.png").write_bytes(PNG)
        self.manifest.write_text(json.dumps({"images": ["picture.png", "second.png"]}))
        self.outbox.prepare(1, self.manifest)
        self.api.send_photo.side_effect = [None, TelegramError("offline")]
        with self.assertRaises(TelegramError):
            self.outbox.deliver(self.job, self.api, authorized=lambda: True)
        restarted = MediaOutbox(self.workspace, self.state)
        self.api.send_photo.reset_mock(side_effect=True)
        restarted.deliver(self.job, self.api, authorized=lambda: True)
        self.api.send_photo.assert_called_once()

    def test_revoke_before_or_between_uploads_blocks_delivery(self):
        self.outbox.prepare(1, self.manifest)
        self.outbox.deliver(self.job, self.api, authorized=lambda: False)
        self.api.send_photo.assert_not_called()

    def test_outside_private_state_and_symlink_paths_are_rejected(self):
        outside = self.workspace.parent / "secret.png"
        outside.write_bytes(PNG)
        (self.workspace / "escape.png").symlink_to(outside)
        (self.state / "private.png").write_bytes(PNG)
        for value in ("../secret.png", str(outside), "state/private.png", "escape.png", ".hidden.png"):
            self.manifest.write_text(json.dumps({"images": [value]}))
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.outbox.prepare(1, self.manifest)
        self.api.send_photo.assert_not_called()

    def test_nonimage_and_too_many_attachments_fail_closed(self):
        self.image.write_bytes(b"not an image")
        with self.assertRaises(ValueError):
            self.outbox.prepare(1, self.manifest)
        self.manifest.write_text(json.dumps({"images": ["picture.png"] * 5}))
        with self.assertRaises(ValueError):
            self.outbox.prepare(1, self.manifest)

    def test_no_manifest_is_a_normal_text_result(self):
        self.outbox.prepare(2, self.state / "jobs/2/missing.json")
        self.outbox.deliver({**self.job, "id": 2}, self.api, authorized=lambda: True)
        self.api.send_photo.assert_not_called()

    def test_permanent_upload_rejection_gives_chat_fallback_and_unblocks_outbox(self):
        self.outbox.prepare(1, self.manifest)
        self.api.send_photo.side_effect = TelegramError("invalid photo", status=400)
        self.outbox.deliver(self.job, self.api, authorized=lambda: True)
        self.api.send_message.assert_called_once()
        self.assertNotIn(str(self.workspace), self.api.send_message.call_args.args[1])
        self.outbox.deliver(self.job, self.api, authorized=lambda: True)
        self.api.send_photo.assert_called_once()

    def test_revocation_between_multiple_photos_stops_next_upload(self):
        (self.workspace / "second.png").write_bytes(PNG)
        self.manifest.write_text(json.dumps({"images": ["picture.png", "second.png"]}))
        self.outbox.prepare(1, self.manifest)
        authorized = Mock(side_effect=[True, False])
        self.outbox.deliver(self.job, self.api, authorized=authorized)
        self.api.send_photo.assert_called_once()

    def test_corrupt_snapshot_never_uploads_modified_content(self):
        self.outbox.prepare(1, self.manifest)
        (self.state / "media/1/0.png").write_bytes(b"changed")
        self.outbox.deliver(self.job, self.api, authorized=lambda: True)
        self.api.send_photo.assert_not_called()
        self.api.send_message.assert_called_once()


    def test_symlinked_snapshot_directory_is_rejected_before_writing(self):
        outside = self.workspace.parent / "outside"
        outside.mkdir()
        (self.state / "media").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.outbox.prepare(1, self.manifest)
        self.assertEqual(list(outside.iterdir()), [])



class UploadTests(unittest.TestCase):
    def test_photo_upload_contains_bytes_and_no_host_path_or_parse_mode(self):
        captured = []
        def opener(request, **kwargs):
            captured.append(request)
            return io.BytesIO(b'{"ok":true,"result":{"message_id":1}}')
        with tempfile.TemporaryDirectory() as root:
            image = Path(root) / "private-name.png"
            image.write_bytes(PNG)
            result = BotAPI("123:fake", opener=opener).send_photo(7, image)
        request = captured[0]
        self.assertTrue(request.full_url.endswith("/sendPhoto"))
        self.assertIn(b'name="photo"', request.data)
        self.assertIn(PNG, request.data)
        self.assertNotIn(b"private-name", request.data)
        self.assertNotIn(b"parse_mode", request.data)
        self.assertEqual(result["message_id"], 1)

    def test_upload_errors_do_not_expose_token_or_url(self):
        def opener(request, **kwargs):
            raise OSError(request.full_url)
        with tempfile.TemporaryDirectory() as root:
            image = Path(root) / "image.png"
            image.write_bytes(PNG)
            with self.assertRaises(TelegramError) as error:
                BotAPI("123:fake", opener=opener).send_photo(7, image)
        self.assertNotIn("123:fake", str(error.exception))


class MediaPipelineTests(unittest.TestCase):
    setUp = MediaTests.setUp

    def test_runner_prepares_only_selected_generated_images_and_service_uploads(self):
        from senai.telegram.runner import CommandRunner
        from senai.telegram.store import JobStore
        from senai.telegram.router import Router
        from senai.telegram.service import BotService
        import subprocess
        store = JobStore(self.state / "state.sqlite3")
        store.bind_shared_session("11111111-1111-4111-8111-111111111111")
        store.consume(1, {"chat_id": 7, "user_id": 7, "prompt": "Create a picture"})
        # CommandRunner owns its new job directory.
        self.manifest.unlink()
        self.manifest.parent.rmdir()
        runner = CommandRunner(self.workspace.parent, self.state, store=store,
                               chat_style=True, media=self.outbox)
        def execute(command, **kwargs):
            self.assertIn("attachments.json", command[-1])
            self.assertIn("image generation", command[-1])
            self.assertNotIn("Current delivery is text-only", command[-1])
            self.manifest.write_text(json.dumps({"images": ["picture.png"]}))
            Path(command[command.index("--output-last-message") + 1]).write_text("Your picture is ready.")
            return subprocess.CompletedProcess(command, 0)
        service = BotService(self.api, store, Router(store, {7}, "bot"), runner, media=self.outbox)
        with patch("senai.telegram.runner.subprocess.run", side_effect=execute):
            self.assertTrue(service.run_one())
        self.api.redact.side_effect = lambda value: value
        service.deliver_results()
        self.api.send_photo.assert_called_once()
        self.assertEqual(store.pending_results(), [])

    def test_media_upload_retry_does_not_repeat_text_or_execute_again(self):
        from senai.telegram.store import JobStore
        from senai.telegram.router import Router
        from senai.telegram.service import BotService
        store = JobStore(self.state / "state.sqlite3")
        store.consume(1, {"chat_id": 7, "user_id": 7, "prompt": "Send picture"})
        store.claim_next()
        self.outbox.prepare(1, self.manifest)
        store.finish(1, "succeeded", "Picture ready.")
        self.api.redact.side_effect = lambda value: value
        runner = Mock()
        service = BotService(self.api, store, Router(store, {7}, "bot"), runner, media=self.outbox)
        self.api.send_photo.side_effect = TelegramError("offline")
        with self.assertRaises(TelegramError):
            service.deliver_results()
        self.api.send_photo.side_effect = None
        service.deliver_results()
        self.api.send_message.assert_called_once()
        runner.assert_not_called()
        self.assertEqual(store.pending_results(), [])
