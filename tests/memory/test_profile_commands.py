import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from senai.memory import InstallationMemory, profile_main, setup_profiles


class TTY(io.StringIO):
    def isatty(self):
        return True


class NoRead(io.StringIO):
    def readline(self, *args):
        raise AssertionError("noninteractive input must not be read")


class ProfileCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out, self.err = io.StringIO(), io.StringIO()
        setup_profiles(self.root)

    def run_command(self, kind, argv, *, stdin=None, installation=None):
        self.out.seek(0); self.out.truncate()
        self.err.seek(0); self.err.truncate()
        return profile_main(kind, argv, installation=self.root if installation is None else installation,
                            stdin=stdin if stdin is not None else io.StringIO(),
                            stdout=self.out, stderr=self.err)

    def file(self, name):
        return self.root / "outputs/.senai-memory" / name

    def test_each_kind_append_show_path_without_database(self):
        for kind, name in (("memory", "MEMORY.md"), ("user", "USER.md"), ("soul", "SOUL.md")):
            with self.subTest(kind=kind):
                self.assertEqual(self.run_command(kind, ["add", "Be concise"]), 0, self.err.getvalue())
                self.assertIn("fresh session", self.out.getvalue())
                self.assertEqual(self.run_command(kind, ["show"]), 0)
                self.assertIn("Be concise", self.out.getvalue())
                self.assertEqual(self.run_command(kind, ["path"]), 0)
                self.assertEqual(self.out.getvalue().strip(), str(self.file(name)))
        self.assertFalse(self.file("memory.db").exists())

    def test_append_preserves_old_text_and_deduplicates(self):
        self.file("MEMORY.md").write_text("# Existing notes\n\n- Uses SQLite")
        self.assertEqual(self.run_command("memory", ["add", "Prefers", "Python"]), 0)
        first = self.file("MEMORY.md").read_text()
        self.assertTrue(first.startswith("# Existing notes\n\n- Uses SQLite"))
        self.assertIn("- Prefers Python", first)
        self.assertEqual(self.run_command("memory", ["add", "prefers   python"]), 0)
        self.assertEqual(self.file("MEMORY.md").read_text(), first)
        self.assertIn("Already", self.out.getvalue())

    def test_missing_text_prompts_with_example_in_tty(self):
        self.assertEqual(self.run_command("user", ["add"], stdin=TTY("Likes quiet output\n")), 0)
        self.assertIn("example", self.out.getvalue().lower())
        self.assertIn("Likes quiet output", self.file("USER.md").read_text())

    def test_noninteractive_missing_text_fails_without_reading(self):
        self.assertEqual(self.run_command("memory", ["add"], stdin=NoRead()), 2)
        self.assertIn('senai memory add "', self.err.getvalue())
        self.assertEqual(self.file("MEMORY.md").read_text(), "")

    def test_empty_eof_cancel_and_invalid_arguments_do_not_save(self):
        for args, stream in ((["add", "  "], io.StringIO()),
                             (["add"], TTY("\n")), (["add"], TTY(""))):
            self.assertEqual(self.run_command("memory", args, stdin=stream), 2)
        class Cancelled(TTY):
            def readline(self, *args):
                raise KeyboardInterrupt()
        self.assertEqual(self.run_command("memory", ["add"], stdin=Cancelled()), 130)
        for args in ([], ["delete"], ["show", "extra"]):
            self.assertEqual(self.run_command("memory", args), 2)
        self.assertEqual(self.file("MEMORY.md").read_text(), "")

    def test_validation_and_capacity_errors_are_actionable_and_sanitized(self):
        for text in ("api_key=example", "x" * 4001):
            self.assertEqual(self.run_command("user", ["add", text]), 2)
            self.assertNotIn(text, self.err.getvalue())
        self.file("USER.md").write_text("x" * 3999)
        self.assertEqual(self.run_command("user", ["add", "Likes Python"]), 2)
        self.assertIn("full", self.err.getvalue())
        self.assertIn("senai user path", self.err.getvalue())
        self.assertEqual(self.file("USER.md").read_text(), "x" * 3999)

    def test_conflict_does_not_overwrite_concurrent_change(self):
        from senai.memory.installation import _InstallationProfiles
        original = _InstallationProfiles.propose
        def changed(store, *args, **kwargs):
            proposal = original(store, *args, **kwargs)
            self.file("MEMORY.md").write_text("Concurrent edit")
            return proposal
        with patch.object(_InstallationProfiles, "propose", changed):
            self.assertEqual(self.run_command("memory", ["add", "A new fact"]), 2)
        self.assertIn("changed", self.err.getvalue())
        self.assertEqual(self.file("MEMORY.md").read_text(), "Concurrent edit")

    def test_human_soul_is_allowed_but_learning_is_still_blocked(self):
        self.assertEqual(self.run_command("soul", ["add", "Speak clearly"]), 0)
        with self.assertRaises(ValueError):
            InstallationMemory(self.root).remember("SOUL.md", "Different", noteworthy=True, verified=True)
        self.assertIn("Speak clearly", self.file("SOUL.md").read_text())

    def test_setup_creates_missing_root_and_profiles_without_overwriting(self):
        new = self.root / "new-install"
        self.assertEqual(self.run_command("memory", ["setup"], installation=new), 0)
        paths = setup_profiles(new)
        self.assertEqual(set(paths), {"SOUL.md", "USER.md", "MEMORY.md"})
        paths["SOUL.md"].write_text("Existing personality")
        setup_profiles(new)
        self.assertEqual(paths["SOUL.md"].read_text(), "Existing personality")
        for path in paths.values():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_unconfigured_or_missing_setup_has_specific_errors_no_implicit_creation(self):
        self.assertEqual(profile_main("memory", ["show"], installation=None, stdin=io.StringIO(),
                                     stdout=self.out, stderr=self.err), 2)
        self.assertIn("senai setup", self.err.getvalue())
        missing = self.root / "missing"
        self.assertEqual(self.run_command("memory", ["add", "Fact"], installation=missing), 2)
        self.assertFalse(missing.exists())
        bare = self.root / "bare"; bare.mkdir()
        self.assertEqual(self.run_command("memory", ["add", "Fact"], installation=bare), 2)
        self.assertIn("setup", self.err.getvalue())
        self.assertFalse((bare / "outputs").exists())

    def test_path_show_help_are_read_only_and_use_injected_streams(self):
        bare = self.root / "bare"; bare.mkdir()
        self.assertEqual(self.run_command("memory", ["path"], installation=bare), 0)
        self.assertIn("MEMORY.md", self.out.getvalue())
        self.assertEqual(self.run_command("memory", ["show"], installation=bare), 0)
        self.assertIn("empty", self.out.getvalue())
        self.assertEqual(self.run_command("memory", ["--help"], installation=bare), 0)
        self.assertIn("add", self.out.getvalue())
        self.assertFalse((bare / "outputs").exists())

    def test_symlink_corruption_and_non_directory_errors_preserve_data(self):
        self.file("MEMORY.md").write_bytes(b"\xff")
        self.assertEqual(self.run_command("memory", ["show"]), 2)
        self.assertIn("UTF-8", self.err.getvalue())
        self.file("MEMORY.md").unlink()
        external = self.root / "external"; external.write_text("Outside")
        self.file("MEMORY.md").symlink_to(external)
        self.assertEqual(self.run_command("memory", ["add", "Fact"]), 2)
        self.assertIn("symlink", self.err.getvalue())
        self.assertEqual(external.read_text(), "Outside")
        self.assertEqual(self.run_command("memory", ["setup"], installation=external), 2)

    def test_frozen_and_fresh_snapshots_after_short_command(self):
        memory = InstallationMemory(self.root)
        self.assertEqual(self.run_command("user", ["add", "Prefers Python"]), 0)
        old = memory.snapshot("preferences")
        self.assertEqual(self.run_command("user", ["add", "Likes concise answers"]), 0)
        self.assertNotIn("Likes concise answers", old.context)
        self.assertIn("Likes concise answers", memory.snapshot("preferences").context)

    def test_advanced_module_api_remains_sqlite_add(self):
        import json
        import subprocess
        import sys
        result = subprocess.run([
            sys.executable, "-m", "senai.memory", "--installation", str(self.root),
            "add", "Detailed fact", "--provenance", "manual"],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["text"], "Detailed fact")
        self.assertEqual(self.file("MEMORY.md").read_text(), "")

    def test_subcommand_help_and_errors_respect_injected_streams(self):
        for args in (["add", "--help"], ["show", "--help"], ["setup", "--help"]):
            self.assertEqual(self.run_command("memory", args), 0)
            self.assertIn("usage:", self.out.getvalue())
        self.assertEqual(self.run_command("memory", ["add", "--unknown"]), 2)
        self.assertIn("--help", self.err.getvalue())

    def test_multiline_explicit_note_is_deduplicated(self):
        text = "First paragraph\n\nSecond paragraph"
        self.assertEqual(self.run_command("memory", ["add", text]), 0)
        before = self.file("MEMORY.md").read_text()
        self.assertEqual(self.run_command("memory", ["add", text]), 0)
        self.assertEqual(self.file("MEMORY.md").read_text(), before)

    def test_feature_local_cli_roundtrip_each_profile(self):
        import subprocess
        import sys
        base = [sys.executable, "-m", "senai.memory.profile_cli", "--installation", str(self.root)]
        for kind in ("memory", "user", "soul"):
            added = subprocess.run(base + [kind, "add", "Human note"], capture_output=True, text=True)
            self.assertEqual(added.returncode, 0, added.stderr)
            shown = subprocess.check_output(base + [kind, "show"], text=True)
            self.assertIn("Human note", shown)
        failed = subprocess.run(base + ["memory", "add"], input="", capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertIn("Provide text", failed.stderr)
