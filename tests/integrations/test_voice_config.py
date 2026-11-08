import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai.telegram.voice_config import (
    VoiceConfigError, default_voice_file, write_voice_key, read_voice_key,
    remove_voice_key, resolve_voice_key, configure_voice, offer_voice_setup,
    speech_from_configuration,
)

KEY = "sk-test-private-voice-value"


class VoiceFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.env = {"XDG_CONFIG_HOME": str(self.root / "config")}
        self.path = default_voice_file(self.project, environ=self.env)

    def test_protected_separate_per_project_file_and_atomic_replacement(self):
        self.assertNotEqual(self.path, default_voice_file(self.root / "other", environ=self.env))
        write_voice_key(self.project, KEY, environ=self.env)
        self.assertFalse(self.path.is_relative_to(self.project))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(read_voice_key(self.project, environ=self.env), KEY)
        write_voice_key(self.project, "sk-replaced", environ=self.env)
        self.assertEqual(read_voice_key(self.project, environ=self.env), "sk-replaced")
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_remove_is_idempotent_and_does_not_touch_telegram_or_project(self):
        marker = self.project / "keep.sqlite3"
        marker.write_bytes(b"unchanged")
        write_voice_key(self.project, KEY, environ=self.env)
        self.assertTrue(remove_voice_key(self.project, environ=self.env))
        self.assertFalse(remove_voice_key(self.project, environ=self.env))
        self.assertIsNone(read_voice_key(self.project, environ=self.env))
        self.assertEqual(marker.read_bytes(), b"unchanged")

    def test_rejects_symlinks_shared_permissions_and_invalid_file_without_leaking(self):
        write_voice_key(self.project, KEY, environ=self.env)
        self.path.chmod(0o644)
        with self.assertRaises(VoiceConfigError):
            read_voice_key(self.project, environ=self.env)
        self.path.chmod(0o600)
        self.path.write_text(KEY + " not JSON")
        with self.assertRaises(VoiceConfigError) as error:
            read_voice_key(self.project, environ=self.env)
        self.assertNotIn(KEY, str(error.exception))
        self.path.unlink()
        target = self.root / "target"
        target.write_text("preserve")
        self.path.symlink_to(target)
        for operation in (lambda: write_voice_key(self.project, KEY, environ=self.env),
                          lambda: read_voice_key(self.project, environ=self.env),
                          lambda: remove_voice_key(self.project, environ=self.env)):
            with self.assertRaises(VoiceConfigError):
                operation()
        self.assertEqual(target.read_text(), "preserve")

    def test_cannot_save_inside_controlled_project_or_git_repository(self):
        for base in (self.project, self.root / "repo"):
            base.mkdir(exist_ok=True)
            if base != self.project:
                (base / ".git").mkdir()
            with self.subTest(base=base), self.assertRaises(VoiceConfigError):
                write_voice_key(self.project, KEY, environ={"XDG_CONFIG_HOME": str(base)})

    def test_invalid_replacement_keeps_existing_key(self):
        write_voice_key(self.project, KEY, environ=self.env)
        for invalid in ("", "a\nb", "a b", "a\x00b"):
            with self.assertRaises(VoiceConfigError):
                write_voice_key(self.project, invalid, environ=self.env)
            self.assertEqual(read_voice_key(self.project, environ=self.env), KEY)

    def test_key_precedence_and_native_environment_are_unchanged(self):
        write_voice_key(self.project, KEY, environ=self.env)
        env = {**self.env, "OPENAI_API_KEY": "native-key"}
        original = env.copy()
        selected = resolve_voice_key(self.project, environ=env)
        self.assertEqual(selected.key, KEY)
        self.assertNotIn(KEY, repr(selected))
        env["SENAI_TTS_API_KEY"] = "dedicated-key"
        self.assertEqual(resolve_voice_key(self.project, environ=env).key, "dedicated-key")
        remove_voice_key(self.project, environ=self.env)
        self.assertEqual(resolve_voice_key(self.project, environ=original).key, "native-key")
        self.assertEqual(original, {**self.env, "OPENAI_API_KEY": "native-key"})

    def test_startup_automatically_constructs_speech_without_mutating_environment(self):
        write_voice_key(self.project, KEY, environ=self.env)
        with patch("senai.telegram.voice_config.OpenAISpeech") as factory:
            speech_from_configuration(self.project, environ=self.env)
        factory.assert_called_once_with(KEY, model="gpt-4o-mini-tts", voice="coral")
        self.assertEqual(self.env, {"XDG_CONFIG_HOME": str(self.root / "config")})

    def test_missing_file_and_no_environment_is_normal_optional_voice(self):
        self.assertIsNone(resolve_voice_key(self.project, environ=self.env))
        self.assertIsNone(speech_from_configuration(self.project, environ=self.env))


class VoiceSetupTests(unittest.TestCase):
    setUp = VoiceFileTests.setUp
    def test_skip_does_not_ask_for_a_key_or_change_existing_configuration(self):
        write_voice_key(self.project, KEY, environ=self.env)
        before = self.path.read_bytes()
        prompt = Mock()
        out = io.StringIO()
        self.assertFalse(offer_voice_setup(self.project, stdout=out, choice=lambda message: "Skip",
                                          prompt=prompt, environ=self.env))
        prompt.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn(KEY, out.getvalue())

    def test_opt_in_uses_hidden_input_and_reports_restart_without_echo(self):
        out = io.StringIO()
        with patch("senai.telegram.voice_config.getpass.getpass", return_value=KEY) as hidden:
            self.assertTrue(offer_voice_setup(self.project, stdout=out, choice=lambda message: "yes", environ=self.env))
        hidden.assert_called_once()
        self.assertEqual(read_voice_key(self.project, environ=self.env), KEY)
        self.assertNotIn(KEY, out.getvalue())
        self.assertIn("graceful", out.getvalue())
        self.assertIn("text and", out.getvalue())

    def test_failed_optional_setup_keeps_telegram_usable_and_old_key_intact(self):
        write_voice_key(self.project, KEY, environ=self.env)
        out = io.StringIO()
        self.assertFalse(offer_voice_setup(self.project, stdout=out, choice=lambda message: "yes",
                                          prompt=Mock(side_effect=OSError(KEY)), environ=self.env))
        self.assertEqual(read_voice_key(self.project, environ=self.env), KEY)
        self.assertNotIn(KEY, out.getvalue())
        self.assertIn("Telegram", out.getvalue())

    def test_noninteractive_choice_defaults_to_skip(self):
        prompt = Mock()
        self.assertFalse(offer_voice_setup(self.project, stdout=io.StringIO(),
                         choice=Mock(side_effect=EOFError), prompt=prompt, environ=self.env))
        prompt.assert_not_called()

    def test_hidden_input_never_falls_back_to_echo(self):
        import getpass
        with patch("senai.telegram.voice_config.getpass.getpass", side_effect=getpass.GetPassWarning("unsafe")):
            with self.assertRaises(VoiceConfigError):
                configure_voice(self.project, stdout=io.StringIO(), environ=self.env)
        self.assertFalse(self.path.exists())
