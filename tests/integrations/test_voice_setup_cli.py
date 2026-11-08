import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai import cli
from senai.telegram.voice_config import default_voice_file, read_voice_key, write_voice_key
from senai.telegram.wizard import Configuration

KEY = "sk-synthetic-voice-key-never-print"


class VoiceCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.env = {"XDG_CONFIG_HOME": str(self.root / "config")}
        self.out, self.err = io.StringIO(), io.StringIO()

    def run_command(self, action):
        return cli.main(["telegram", "--project", str(self.project), action], self.out, self.err)

    def test_configure_replace_check_remove_need_no_telegram_token_or_bot(self):
        with patch.dict(os.environ, self.env, clear=True), patch("senai.telegram.cli.BotAPI") as api, patch(
                "senai.telegram.cli.BotService") as service, patch("senai.telegram.cli.JobStore") as store, patch(
                "senai.telegram.voice_config.getpass.getpass", side_effect=[KEY, "sk-replacement"]):
            self.assertEqual(self.run_command("--voice-configure"), 0)
            self.assertEqual(read_voice_key(self.project), KEY)
            self.assertEqual(self.run_command("--voice-configure"), 0)
            self.assertEqual(read_voice_key(self.project), "sk-replacement")
            self.assertEqual(self.run_command("--voice-check"), 0)
            self.assertEqual(self.run_command("--voice-remove"), 0)
            self.assertIsNone(read_voice_key(self.project))
            self.assertEqual(self.run_command("--voice-check"), 1)
            self.assertEqual(self.run_command("--voice-remove"), 0)
        api.assert_not_called()
        service.assert_not_called()
        store.assert_not_called()
        self.assertNotIn(KEY, self.out.getvalue() + self.err.getvalue())
        self.assertNotIn("sk-replacement", self.out.getvalue() + self.err.getvalue())
        self.assertIn("Local check", self.out.getvalue())
        self.assertIn("graceful", self.out.getvalue())

    def test_read_errors_and_hidden_prompt_errors_are_redacted(self):
        with patch.dict(os.environ, self.env, clear=True), patch(
                "senai.telegram.voice_config.getpass.getpass", side_effect=OSError(KEY)):
            self.assertEqual(self.run_command("--voice-configure"), 2)
        self.assertNotIn(KEY, self.err.getvalue())
        write_voice_key(self.project, KEY, environ=self.env)
        path = default_voice_file(self.project, environ=self.env)
        path.write_text(KEY + " malformed")
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(self.run_command("--voice-check"), 2)
        self.assertNotIn(KEY, self.err.getvalue())

    def test_accidental_key_argument_is_rejected_without_echoing_it(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit) as error:
            cli.main(["telegram", "--voice-configure", KEY], self.out, self.err)
        self.assertEqual(error.exception.code, 2)
        self.assertNotIn(KEY, output.getvalue() + self.out.getvalue() + self.err.getvalue())

    def test_existing_env_users_need_no_file_and_removal_does_not_unset_environment(self):
        env = {**self.env, "SENAI_TTS_API_KEY": KEY, "OPENAI_API_KEY": "native-auth"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(self.run_command("--voice-check"), 0)
            self.assertEqual(self.run_command("--voice-remove"), 0)
            self.assertEqual(os.environ["SENAI_TTS_API_KEY"], KEY)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "native-auth")
        self.assertFalse(default_voice_file(self.project, environ=self.env).exists())
        self.assertIn("Environment", self.out.getvalue())


class TelegramVoiceStartupTests(unittest.TestCase):
    setUp = VoiceCommandTests.setUp
    def start(self, configure=False, choice="Skip", key=KEY):
        api = Mock()
        api.get_me.return_value = {"id": 123, "is_bot": True, "username": "test_bot"}
        api.get_webhook_info.return_value = {"url": ""}
        api.get_updates.return_value = []
        args = ["telegram", "--project", str(self.project)]
        if configure:
            args += ["--configure", "--start"]
        env = dict(self.env)
        if not configure:
            env["TELEGRAM_BOT_TOKEN"] = "123:synthetic"
        with patch.dict(os.environ, env, clear=True), patch("senai.telegram.cli.BotAPI", return_value=api), patch(
                "senai.telegram.cli.BotService") as service, patch("senai.telegram.cli.CommandRunner") as runner, patch(
                "senai.telegram.wizard.configure_project", return_value=Configuration("123:synthetic", self.root / "telegram.env", "test_bot")), patch(
                "builtins.input", return_value=choice), patch("senai.telegram.voice_config.getpass.getpass", return_value=key):
            service.return_value.run_forever.return_value = 0
            result = cli.main(args, self.out, self.err)
        return result, runner, service

    def test_initial_setup_offer_can_be_skipped_and_telegram_still_starts(self):
        result, runner, service = self.start(configure=True)
        self.assertEqual(result, 0)
        self.assertIsNone(runner.call_args.kwargs["speech"])
        service.return_value.run_forever.assert_called_once()
        self.assertFalse(default_voice_file(self.project, environ=self.env).exists())
        self.assertIn("Optional voice", self.out.getvalue())

    def test_initial_opt_in_saves_and_loads_voice_for_the_first_start(self):
        result, runner, service = self.start(configure=True, choice="Configure")
        self.assertEqual(result, 0)
        self.assertIsNotNone(runner.call_args.kwargs["speech"])
        self.assertEqual(read_voice_key(self.project, environ=self.env), KEY)
        self.assertNotIn(KEY, self.out.getvalue() + self.err.getvalue())

    def test_existing_saved_key_loads_on_later_start_without_any_setup_prompt(self):
        write_voice_key(self.project, KEY, environ=self.env)
        with patch("senai.telegram.cli.offer_voice_setup", side_effect=AssertionError("must not prompt")) as offer:
            result, runner, service = self.start()
        self.assertEqual(result, 0)
        self.assertIsNotNone(runner.call_args.kwargs["speech"])
        offer.assert_not_called()

    def test_initial_setup_without_start_still_offers_skip(self):
        configured = Configuration("123:synthetic", self.root / "telegram.env", "test_bot")
        with patch.dict(os.environ, self.env, clear=True), patch("senai.telegram.wizard.configure_project", return_value=configured), patch(
                "senai.telegram.cli.BotService") as service, patch("builtins.input", return_value="Skip"):
            result = cli.main(["telegram", "--project", str(self.project), "--configure"], self.out, self.err)
        self.assertEqual(result, 0)
        service.assert_not_called()
        self.assertIn("Optional voice", self.out.getvalue())

    def test_bad_optional_file_does_not_prevent_existing_text_bot_start(self):
        write_voice_key(self.project, KEY, environ=self.env)
        default_voice_file(self.project, environ=self.env).chmod(0o644)
        result, runner, service = self.start()
        self.assertEqual(result, 0)
        self.assertIsNone(runner.call_args.kwargs["speech"])
        service.return_value.run_forever.assert_called_once()
        self.assertNotIn(KEY, self.out.getvalue() + self.err.getvalue())


class ExistingStateCompatibilityTests(unittest.TestCase):
    setUp = VoiceCommandTests.setUp
    run_command = VoiceCommandTests.run_command

    def test_management_preserves_telegram_token_jobs_pairing_media_and_exact_session(self):
        from senai.telegram.config import default_env_file, write_token_file
        from senai.telegram.store import JobStore
        from senai.telegram.media import MediaOutbox
        import hashlib
        state = self.project / "outputs/.senai-telegram/123"
        store = JobStore(state / "state.sqlite3")
        sid = "11111111-1111-4111-8111-111111111111"
        store.bind_shared_session(sid)
        store.set_user_status(7, True)
        store.consume(1, {"chat_id": 7, "user_id": 7, "prompt": "Existing queued request"})
        MediaOutbox(self.project / "outputs", state)
        # Keep this fixture independent of the operator's actual config home.
        with patch.dict(os.environ, self.env, clear=True):
            token_path = default_env_file(self.project)
            write_token_file(token_path, "123:existing-token")
        before = {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in state.rglob("*") if file.is_file()}
        token_before = token_path.read_bytes()
        with patch.dict(os.environ, self.env, clear=True), patch(
                "senai.telegram.voice_config.getpass.getpass", side_effect=[KEY, "sk-new-key"]):
            for action in ("--voice-configure", "--voice-check", "--voice-configure", "--voice-remove"):
                self.assertEqual(self.run_command(action), 0)
        after = {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in state.rglob("*") if file.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(token_path.read_bytes(), token_before)
        self.assertEqual(store.shared_session(), sid)
        self.assertTrue(store.user_status(7))
        self.assertEqual(store.claim_next()["prompt"], "Existing queued request")
