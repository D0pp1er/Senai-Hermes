import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai.telegram.api import BotAPI, TelegramError
from senai.telegram.media import MediaOutbox
from senai.telegram.router import Router
from senai.telegram.runner import CommandRunner
from senai.telegram.service import BotService
from senai.telegram.speech import OpenAISpeech, SpeechError, speech_from_environment
from senai.telegram.store import JobStore

AUDIO = b"ID3" + b"fake audio fixture"


def update(identifier=1, text="/voice What is Python?", user=7):
    return {"update_id": identifier, "message": {"from": {"id": user},
            "chat": {"id": user, "type": "private"}, "text": text}}


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "outputs/state"
        self.store = JobStore(self.state / "state.sqlite3")
        self.media = MediaOutbox(self.root / "outputs", self.state)
        self.speech = Mock(return_value=AUDIO)
        self.api = Mock()
        self.api.redact.side_effect = lambda text: text
        self.router = Router(self.store, {7}, "test_bot", voice_enabled=True, media=self.media)
        self.runner = CommandRunner(self.root, self.state, store=self.store,
                                    chat_style=True, media=self.media, speech=self.speech)
        self.service = BotService(self.api, self.store, self.router, self.runner, media=self.media)

    def execute(self, command, **kwargs):
        self.assertNotIn("/voice", command[-1])
        self.assertIn("spoken", command[-1])
        self.assertNotIn("SENAI_TTS_API_KEY", kwargs["env"])
        kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id":
                                 "11111111-1111-4111-8111-111111111111"}))
        Path(command[command.index("--output-last-message") + 1]).write_text("Python is a programming language.")
        return subprocess.CompletedProcess(command, 0)

    def test_voice_question_uploads_only_an_ai_disclosed_voice_note(self):
        self.router.handle(update())
        with patch.dict("os.environ", {"SENAI_TTS_API_KEY": "fake-speech-key"}), patch(
                "senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        self.speech.assert_called_once_with("Python is a programming language.")
        self.service.deliver_results()
        self.api.send_message.assert_not_called()
        self.api.send_voice.assert_called_once()
        self.assertEqual(self.api.send_voice.call_args.args[0], 7)
        self.assertEqual(Path(self.api.send_voice.call_args.args[1]).read_bytes(), AUDIO)

    def test_bare_voice_speaks_latest_own_answer_without_model_execution(self):
        self.store.consume(1, {"chat_id": 7, "user_id": 7, "prompt": "Hi"})
        self.store.claim_next()
        self.store.finish(1, "succeeded", "Hello there.")
        self.store.mark_delivered(1)
        self.router.handle(update(2, "/voice"))
        with patch("senai.telegram.runner.subprocess.run") as execute:
            self.service.run_one()
        execute.assert_not_called()
        self.speech.assert_called_once_with("Hello there.")
        self.service.deliver_results()
        self.api.send_voice.assert_called_once()
        self.api.send_message.assert_not_called()

    def test_voice_is_single_reply_not_a_global_or_per_user_mode(self):
        self.router.handle(update())
        self.assertEqual(self.store.claim_next()["prompt"], "What is Python?")
        self.router.handle(update(2, "Normal text"))
        self.assertEqual(self.store.claim_next()["prompt"], "Normal text")

    def test_missing_credentials_uses_normal_text_execution_as_fallback(self):
        router = Router(self.store, {7}, "test_bot", voice_enabled=False, media=self.media)
        router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute_text):
            self.service.run_one()
        self.service.deliver_results()
        self.api.send_message.assert_called_once_with(7, "Python is a programming language.")
        self.speech.assert_not_called()
        self.api.send_voice.assert_not_called()

    def execute_text(self, command, **kwargs):
        kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id":
                                 "11111111-1111-4111-8111-111111111111"}))
        Path(command[command.index("--output-last-message") + 1]).write_text("Python is a programming language.")
        return subprocess.CompletedProcess(command, 0)

    def test_bare_voice_without_credentials_falls_back_to_latest_text(self):
        self.store.consume(1, {"chat_id": 7, "user_id": 7, "prompt": "Hi"})
        self.store.claim_next()
        self.store.finish(1, "succeeded", "Hello there.")
        self.store.mark_delivered(1)
        router = Router(self.store, {7}, "test_bot", voice_enabled=False)
        self.assertEqual(router.handle(update(2, "/voice")), [(7, "Hello there.")])
        self.assertIsNone(self.store.claim_next())

    def test_unauthorized_duplicate_and_busy_voice_requests_do_not_execute(self):
        self.assertEqual(self.router.handle(update(user=9)), [])
        self.router.max_pending = 1
        self.router.handle(update(2))
        self.assertEqual(self.router.handle(update(2)), [])
        self.assertIn("busy", self.router.handle(update(3))[0][1])
        self.speech.assert_not_called()

    def test_no_previous_answer_gives_help_and_does_not_queue(self):
        self.assertIn("/voice your question", self.router.handle(update(text="/voice"))[0][1])
        self.assertIsNone(self.store.claim_next())

    def test_speech_failure_preserves_text_and_does_not_claim_voice_delivery(self):
        self.speech.side_effect = SpeechError("speech unavailable")
        self.router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        self.service.deliver_results()
        text = self.api.send_message.call_args.args[1]
        self.assertIn("Python is a programming language.", text)
        self.assertIn("could not generate", text)
        self.api.send_voice.assert_not_called()

    def test_upload_failure_falls_back_to_text_without_regenerating_or_late_audio(self):
        self.router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        self.api.send_voice.side_effect = TelegramError("offline")
        self.service.deliver_results()
        self.api.send_message.assert_called_once_with(7, "Python is a programming language.")
        self.api.send_voice.assert_called_once()
        self.api.send_voice.side_effect = None
        restarted = BotService(self.api, JobStore(self.store.path), self.router,
                               self.runner, media=MediaOutbox(self.root / "outputs", self.state))
        restarted.deliver_results()
        self.speech.assert_called_once()
        self.api.send_voice.assert_called_once()
        self.assertEqual(self.store.pending_results(), [])

    def test_failed_text_fallback_retries_only_text_after_restart(self):
        self.router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        self.api.send_voice.side_effect = TelegramError("offline")
        self.api.send_message.side_effect = TelegramError("offline too")
        with self.assertRaises(TelegramError):
            self.service.deliver_results()
        self.api.send_message.side_effect = None
        self.api.send_voice.side_effect = None
        restarted = BotService(self.api, JobStore(self.store.path), self.router,
                               self.runner, media=MediaOutbox(self.root / "outputs", self.state))
        restarted.deliver_results()
        self.api.send_voice.assert_called_once()
        self.speech.assert_called_once()
        self.assertEqual(self.store.pending_results(), [])

    def test_missing_audio_snapshot_falls_back_to_full_answer(self):
        self.router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        (self.state / "media/1/voice.mp3").unlink()
        self.service.deliver_results()
        self.api.send_voice.assert_not_called()
        self.api.send_message.assert_called_once_with(7, "Python is a programming language.")

    def test_successful_voice_is_not_repeated_if_job_finalization_retries(self):
        self.router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        with patch.object(self.store, "mark_delivered", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.service.deliver_results()
        self.service.deliver_results()
        self.api.send_voice.assert_called_once()
        self.api.send_message.assert_not_called()

    def test_legacy_partial_text_reply_finishes_as_text_without_adding_audio(self):
        self.router.handle(update())
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            self.service.run_one()
        self.store.delivery_snapshot(1, ["Previously sent text", "Remaining text"])
        self.store.mark_part_sent(1)
        self.service.deliver_results()
        self.api.send_message.assert_called_once_with(7, "Remaining text")
        self.api.send_voice.assert_not_called()

    def test_voice_command_does_not_send_a_text_acknowledgement(self):
        self.router.acknowledge = Mock(return_value="Working on it.")
        self.assertEqual(self.router.handle(update()), [])
        self.router.acknowledge.assert_not_called()
        self.assertIsNotNone(self.store.claim_next())

    def test_queued_voice_intent_survives_restart_without_changing_session_policy(self):
        self.router.handle(update())
        restarted_media = MediaOutbox(self.root / "outputs", self.state)
        runner = CommandRunner(self.root, self.state, store=JobStore(self.store.path),
                               chat_style=True, media=restarted_media, speech=self.speech)
        service = BotService(self.api, JobStore(self.store.path), self.router, runner, media=restarted_media)
        with patch("senai.telegram.runner.subprocess.run", side_effect=self.execute):
            service.run_one()
        service.deliver_results()
        self.speech.assert_called_once()
        self.api.send_voice.assert_called_once()
        self.assertEqual(self.store.shared_session(), "11111111-1111-4111-8111-111111111111")

    def test_revocation_blocks_queued_speech_and_pending_audio(self):
        self.router.handle(update())
        self.store.set_user_status(7, False)
        with patch("senai.telegram.runner.subprocess.run") as execute:
            self.service.run_one()
        execute.assert_not_called()
        self.speech.assert_not_called()
        self.service.deliver_results()
        self.api.send_voice.assert_not_called()
        self.api.send_message.assert_not_called()

    def test_bare_voice_cannot_read_another_users_answer(self):
        self.store.consume(1, {"chat_id": 8, "user_id": 8, "prompt": "Private"})
        self.store.claim_next()
        self.store.finish(1, "succeeded", "Other users text")
        response = self.router.handle(update(2, "/voice"))
        self.assertIn("No answer", response[0][1])
        self.assertIsNone(self.store.claim_next())



class SpeechClientTests(unittest.TestCase):
    def test_request_is_openai_speech_mp3_and_bounded(self):
        requests = []
        def opener(request, **kwargs):
            requests.append(request)
            return io.BytesIO(AUDIO)
        self.assertEqual(OpenAISpeech("fake", opener=opener)("Hello"), AUDIO)
        self.assertEqual(requests[0].full_url, "https://api.openai.com/v1/audio/speech")
        payload = json.loads(requests[0].data)
        self.assertEqual(payload["input"], "Hello")
        self.assertEqual(payload["response_format"], "mp3")
        with self.assertRaises(SpeechError):
            OpenAISpeech("fake", opener=opener)("x" * 4001)
        self.assertEqual(len(requests), 1)

    def test_key_optional_and_errors_never_expose_credentials(self):
        self.assertIsNone(speech_from_environment({}))
        self.assertIsNotNone(speech_from_environment({"OPENAI_API_KEY": "fake"}))
        self.assertIsNotNone(speech_from_environment({"SENAI_TTS_API_KEY": "speech-only-fake"}))
        def opener(request, **kwargs):
            raise OSError("fake-key sensitive error")
        with self.assertRaises(SpeechError) as error:
            OpenAISpeech("fake-key", opener=opener)("Hello")
        self.assertNotIn("fake-key", str(error.exception))

    def test_invalid_audio_is_not_attached(self):
        with self.assertRaises(SpeechError):
            OpenAISpeech("fake", opener=lambda *args, **kwargs: io.BytesIO(b"not audio"))("Hello")

    def test_voice_upload_includes_ai_disclosure(self):
        requests = []
        def opener(request, **kwargs):
            requests.append(request)
            return io.BytesIO(b'{"ok":true,"result":{}}')
        with tempfile.TemporaryDirectory() as root:
            audio = Path(root) / "private.mp3"
            audio.write_bytes(AUDIO)
            BotAPI("123:fake", opener=opener).send_voice(7, audio)
        request = requests[0]
        self.assertTrue(request.full_url.endswith("/sendVoice"))
        self.assertIn(b'name="voice"', request.data)
        self.assertIn(b"AI-generated voice", request.data)
        self.assertNotIn(b"private.mp3", request.data)


class LiteralRequestTests(unittest.TestCase):
    def test_run_with_literal_voice_prefix_is_not_treated_as_voice_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "outputs/state"
            store = JobStore(state / "state.sqlite3")
            media = MediaOutbox(root / "outputs", state)
            speech = Mock(return_value=AUDIO)
            router = Router(store, {7}, "test_bot", voice_enabled=True, media=media)
            router.handle(update(text="/run /voice literal text"))
            job = store.claim_next()
            runner = CommandRunner(root, state, store=store, media=media, speech=speech)
            def execute(command, **kwargs):
                self.assertEqual(command[-1], "/voice literal text")
                kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id":
                                         "11111111-1111-4111-8111-111111111111"}))
                Path(command[command.index("--output-last-message") + 1]).write_text("Done.")
                return subprocess.CompletedProcess(command, 0)
            with patch("senai.telegram.runner.subprocess.run", side_effect=execute):
                self.assertEqual(runner(job), ("succeeded", "Done."))
            speech.assert_not_called()


class NativeCredentialCompatibilityTests(unittest.TestCase):
    def test_speech_key_is_filtered_without_removing_native_codex_api_auth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = JobStore(root / "outputs/state/state.sqlite3")
            runner = CommandRunner(root, store.path.parent, store=store)
            def execute(command, **kwargs):
                self.assertEqual(kwargs["env"].get("OPENAI_API_KEY"), "native-fake-key")
                self.assertNotIn("SENAI_TTS_API_KEY", kwargs["env"])
                kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id":
                                         "11111111-1111-4111-8111-111111111111"}))
                Path(command[command.index("--output-last-message") + 1]).write_text("Done.")
                return subprocess.CompletedProcess(command, 0)
            with patch.dict("os.environ", {"OPENAI_API_KEY": "native-fake-key", "SENAI_TTS_API_KEY": "speech-fake-key"}), patch(
                    "senai.telegram.runner.subprocess.run", side_effect=execute):
                self.assertEqual(runner({"id": 1, "prompt": "Literal request"}), ("succeeded", "Done."))
