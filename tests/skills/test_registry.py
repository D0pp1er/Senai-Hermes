import tempfile
import unittest
from pathlib import Path

from senai.skills import Registry, SkillError


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "fixture"
        self.source.mkdir()
        self.document = "---\nname: sample\ndescription: Example workflow\nversion: 1.0\n---\nRun the checks before reporting success.\n"
        self.write()
        self.registry = Registry(self.root / "registry")

    def write(self, text=None):
        (self.source / "SKILL.md").write_text(text or self.document)

    def test_import_select_and_restart_preserves_provenance(self):
        (self.source / "reference.txt").write_text("Reference data")
        skill = self.registry.import_local(self.source)
        self.assertEqual(skill.name, "sample")
        self.assertEqual(skill.version, "1.0")
        self.assertEqual(skill.source, str(self.source.resolve()))
        self.assertEqual(skill.validation, "passed")
        restarted = Registry(self.root / "registry")
        self.assertEqual(restarted.list(), [skill])
        selected = restarted.select(["sample"])
        self.assertEqual(selected[0].instructions, "Run the checks before reporting success.\n")
        self.assertEqual((selected[0].path.parent / "reference.txt").read_text(), "Reference data")
        self.assertEqual(len(skill.digest), 64)

    def test_explicit_selection_injects_context_into_executor(self):
        self.registry.import_local(self.source)
        calls = []
        result = self.registry.execute("Check project", ["sample"], executor=lambda request, skills: calls.append((request, skills)) or "done")
        self.assertEqual(result, "done")
        self.assertEqual(calls[0][0], "Check project")
        self.assertEqual(calls[0][1][0].name, "sample")

    def test_duplicate_and_conflicting_names_leave_original_active(self):
        original = self.registry.import_local(self.source)
        for text in (self.document, self.document.replace("1.0", "2.0")):
            self.write(text)
            with self.assertRaises(SkillError):
                self.registry.import_local(self.source)
            self.assertEqual(self.registry.list(), [original])

    def test_malformed_and_unsupported_metadata_never_activate(self):
        for text in ("No header", "---\nname: ../escape\ndescription: Bad\n---\nBody", self.document.replace("version: 1.0", "tools: shell"), self.document.replace("description: Example workflow\n", ""), self.document.replace("name: sample", "name: sample\nname: other")):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaises(SkillError):
                    self.registry.import_local(self.source)
                self.assertEqual(self.registry.list(), [])

    def test_symlinks_are_rejected_even_inside_package(self):
        (self.source / "link").symlink_to(self.source / "SKILL.md")
        with self.assertRaises(SkillError):
            self.registry.import_local(self.source)
        self.assertEqual(self.registry.list(), [])

    def test_symlink_source_and_archives_are_rejected(self):
        link = self.root / "link"
        link.symlink_to(self.source, target_is_directory=True)
        archive = self.root / "escape.zip"
        archive.write_bytes(b"not extracted")
        for source in (link, archive):
            with self.assertRaises(SkillError):
                self.registry.import_local(source)

    def test_missing_selection_and_escaping_names_fail(self):
        for name in ("missing", "../escape", "/absolute"):
            with self.assertRaises(SkillError):
                self.registry.select([name])

    def test_modified_registry_content_is_not_loaded(self):
        skill = self.registry.import_local(self.source)
        skill.path.write_text(self.document.replace("checks", "scripts"))
        with self.assertRaises(SkillError):
            self.registry.select(["sample"])

    def test_import_never_runs_scripts(self):
        marker = self.root / "executed"
        (self.source / "run.sh").write_text("touch " + str(marker))
        self.registry.import_local(self.source)
        self.assertFalse(marker.exists())
