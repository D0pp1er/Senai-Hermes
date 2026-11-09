import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from senai.skills import Check, Registry, SkillError
from senai.skills.obsidian import export_vault
from senai.skills.run import run_request
from senai.skills.cli import main


class ObsidianTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        source = self.project / "source"
        source.mkdir()
        self.document = "---\nname: imported\ndescription: Imported example\nversion: 1\n---\nPreserve leading zeros.\n"
        (source / "SKILL.md").write_text(self.document)
        self.registry = Registry(self.project / "outputs/skills")
        self.original = self.registry.import_local(source)
        self.vault = self.project / "outputs/skills-vault"

    def export(self):
        return export_vault(self.registry, project=self.project)

    def make_learned(self):
        def executor(prompt, workspace, *, options):
            path = Path(workspace) / "learned"
            path.mkdir()
            (path / "SKILL.md").write_text(self.document.replace("name: imported", "name: learned"))
            return "Created"
        run = run_request(self.registry, "Create a reusable procedure", ["imported"], project=self.project, executor=executor, checker=lambda *args: (Check("artifact", True, "Observed package"),))
        candidate = self.registry.stage_learning(run.id, path="learned", reason="Remember the checked identifier workflow")
        self.registry.check_learning(candidate.id, validator=lambda candidate: (Check("leading zeros", True, "Observed identifiers preserved"),))
        return self.registry.accept_learning(candidate.id)

    def test_imported_and_learned_pages_have_origin_links_and_small_history(self):
        self.make_learned()
        result = self.export()
        self.assertEqual(result.skill_count, 2)
        index = (self.vault / "Generated/Index.md").read_text()
        self.assertIn("[[Generated/Skills/learned|learned]]", index)
        self.assertIn("Learned here", index)
        self.assertIn("Imported", index)
        note = (self.vault / "Generated/Skills/learned.md").read_text()
        properties = yaml.safe_load(note.split("---", 2)[1])
        self.assertEqual(properties["origin"], "learned_here")
        self.assertEqual(properties["version"], "1")
        self.assertIn("Preserve leading zeros.", note)
        self.assertIn("[[Generated/History/learned|History]]", note)
        history = (self.vault / "Generated/History/learned.md").read_text()
        self.assertIn("Remember the checked identifier workflow", history)
        self.assertIn("1/1", history)
        self.assertNotIn("Create a reusable procedure", history)

    def test_empty_registry_exports_honest_empty_index(self):
        empty = Registry(self.project / "outputs/empty")
        result = export_vault(empty, project=self.project)
        self.assertEqual(result.skill_count, 0)
        self.assertIn("No saved skills", Path(result.index_path).read_text())

    def test_export_does_not_modify_registry_or_packages(self):
        database = self.registry.root / "registry.sqlite3"
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        document = self.original.path.read_bytes()
        self.export()
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)
        self.assertEqual(self.original.path.read_bytes(), document)

    def test_refresh_preserves_personal_notes_settings_and_unowned_generated_notes(self):
        self.export()
        (self.vault / ".obsidian").mkdir()
        (self.vault / ".obsidian/app.json").write_text('{"theme":"dark"}')
        (self.vault / "My notes.md").write_text("Keep my notes")
        (self.vault / "Generated/Personal.md").write_text("Keep this too")
        self.export()
        self.assertEqual((self.vault / "My notes.md").read_text(), "Keep my notes")
        self.assertEqual((self.vault / "Generated/Personal.md").read_text(), "Keep this too")
        self.assertEqual((self.vault / ".obsidian/app.json").read_text(), '{"theme":"dark"}')

    def test_edited_generated_page_is_not_silently_overwritten(self):
        self.export()
        note = self.vault / "Generated/Skills/imported.md"
        note.write_text("My edited generated note")
        old_index = (self.vault / "Generated/Index.md").read_text()
        with self.assertRaises(SkillError):
            self.export()
        self.assertEqual(note.read_text(), "My edited generated note")
        self.assertEqual((self.vault / "Generated/Index.md").read_text(), old_index)

    def test_vault_symlinks_and_source_namespace_escape_are_rejected(self):
        outside = self.project / "outside"
        outside.mkdir()
        self.vault.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(SkillError):
            self.export()
        self.assertEqual(list(outside.iterdir()), [])
        other = self.project / "other"
        other.mkdir()
        with self.assertRaises(SkillError):
            export_vault(self.registry, project=other)

    def test_failure_during_directory_swap_restores_previous_export(self):
        self.export()
        original_index = (self.vault / "Generated/Index.md").read_text()
        actual_replace = os.replace
        def fail_stage(source, destination):
            if Path(source).name.startswith(".senai-stage-"):
                raise OSError("Injected swap failure")
            return actual_replace(source, destination)
        with patch("senai.skills.obsidian.os.replace", side_effect=fail_stage):
            with self.assertRaises(OSError):
                self.export()
        self.assertEqual((self.vault / "Generated/Index.md").read_text(), original_index)

    def test_revision_and_rollback_refresh_history_without_changing_imported_origin(self):
        self.export()
        outcome = self.registry.record_outcome("imported", digest=self.original.digest, request="Try", result="Wrong", checks=(Check("case", False, "Observed failure"),))
        revision = self.registry.propose_revision("imported", document=self.document.replace("version: 1", "version: 2").replace("Preserve leading zeros.", "Preserve all identifier strings and leading zeros."), outcome_ids=(outcome.id,), reason="Fix identifier loss")
        self.registry.validate_revision(revision.id, validator=lambda *args: (Check("case", True, "Observed pass"),))
        self.registry.activate_revision(revision.id)
        self.export()
        self.assertIn('version: "2"', (self.vault / "Generated/Skills/imported.md").read_text())
        self.registry.rollback("imported", digest=self.original.digest, reason="Restore original instructions")
        self.export()
        history = (self.vault / "Generated/History/imported.md").read_text()
        self.assertIn("Restore original instructions", history)
        self.assertIn("Fix identifier loss", history)
        self.assertIn('origin: "imported"', (self.vault / "Generated/Skills/imported.md").read_text())

    def test_cli_export_returns_vault_and_index_paths(self):
        out, err = io.StringIO(), io.StringIO()
        code = main(["--project", str(self.project), "export-obsidian"], stdout=out, stderr=err)
        self.assertEqual(code, 0, err.getvalue())
        result = json.loads(out.getvalue())
        self.assertEqual(result["skill_count"], 1)
        self.assertTrue(Path(result["index_path"]).is_file())
        self.assertEqual(Path(result["vault_path"]), self.vault)

    def test_untrusted_instruction_markup_is_literal_in_exported_note(self):
        source = self.project / "markup"
        source.mkdir()
        (source / "SKILL.md").write_text(self.document.replace("name: imported", "name: markup").replace("Preserve leading zeros.", "![[Other note]]\n<script>do_not_run()</script>\n```dataviewjs\nalert('not code to execute')\n```"))
        self.registry.import_local(source)
        self.export()
        note = (self.vault / "Generated/Skills/markup.md").read_text()
        self.assertIn("````text", note)
        self.assertIn("<script>do_not_run()</script>", note)

    def test_unmanaged_generated_folder_is_not_overwritten(self):
        folder = self.vault / "Generated"
        folder.mkdir(parents=True)
        (folder / "Index.md").write_text("Personal index")
        with self.assertRaises(SkillError):
            self.export()
        self.assertEqual((folder / "Index.md").read_text(), "Personal index")

    def test_registry_change_during_export_keeps_previous_index(self):
        self.export()
        old = (self.vault / "Generated/Index.md").read_text()
        metadata = self.registry.metadata
        def concurrent(name):
            self.registry.record_outcome(name, digest=self.original.digest, request="Concurrent request", result="Not checked")
            return metadata(name)
        with patch.object(self.registry, "metadata", side_effect=concurrent):
            with self.assertRaises(SkillError):
                self.export()
        self.assertEqual((self.vault / "Generated/Index.md").read_text(), old)

    def test_new_page_cannot_overwrite_unowned_note(self):
        self.export()
        personal = self.vault / "Generated/Skills/new.md"
        personal.write_text("My separate note")
        source = self.project / "new"
        source.mkdir()
        (source / "SKILL.md").write_text(self.document.replace("name: imported", "name: new"))
        self.registry.import_local(source)
        with self.assertRaises(SkillError):
            self.export()
        self.assertEqual(personal.read_text(), "My separate note")

    def test_interrupted_swap_backup_can_be_recovered(self):
        self.export()
        original = (self.vault / "Generated/Index.md").read_text()
        os.replace(self.vault / "Generated", self.vault / ".senai-backup-interrupted")
        self.export()
        self.assertEqual((self.vault / "Generated/Index.md").read_text(), original)

    def test_explicit_local_destination_can_be_created_and_refreshed(self):
        local = self.project / "windows-local-copy"
        result = export_vault(self.registry, project=self.project, destination=local)
        self.assertEqual(Path(result.vault_path), local)
        (local / "Personal.md").write_text("Keep local notes")
        export_vault(self.registry, project=self.project, destination=local)
        self.assertEqual((local / "Personal.md").read_text(), "Keep local notes")
        self.assertTrue((local / "Generated/Skills/imported.md").is_file())

    def test_windows_path_is_translated_without_using_a_shell(self):
        local = self.project / "mounted-windows-copy"
        import subprocess
        completed = subprocess.CompletedProcess([], 0, str(local) + "\n", "")
        with patch("senai.skills.obsidian.subprocess.run", return_value=completed) as command:
            result = export_vault(self.registry, project=self.project, destination="C:\\Users\\example\\SkillsVault")
        self.assertEqual(command.call_args.args[0], ["wslpath", "-u", "C:\\Users\\example\\SkillsVault"])
        self.assertNotIn("shell", command.call_args.kwargs)
        self.assertEqual(result.windows_path, "C:\\Users\\example\\SkillsVault")
        self.assertTrue((local / "Generated/Index.md").is_file())

    def test_verified_manual_copy_is_adopted_without_overwriting_user_settings(self):
        import shutil
        self.export()
        local = self.project / "manual-copy"
        shutil.copytree(self.vault, local)
        (local / "Generated/.senai-manifest.json").unlink()
        (local / ".obsidian").mkdir()
        (local / ".obsidian/app.json").write_text("{}")
        export_vault(self.registry, project=self.project, destination=local)
        self.assertTrue((local / "Generated/.senai-manifest.json").is_file())
        self.assertEqual((local / ".obsidian/app.json").read_text(), "{}")

    def test_changed_manual_copy_is_not_adopted(self):
        import shutil
        self.export()
        local = self.project / "manual-copy"
        shutil.copytree(self.vault, local)
        (local / "Generated/.senai-manifest.json").unlink()
        note = local / "Generated/Skills/imported.md"
        note.write_text("My edited note")
        with self.assertRaises(SkillError):
            export_vault(self.registry, project=self.project, destination=local)
        self.assertEqual(note.read_text(), "My edited note")

    def test_destination_cannot_overlap_the_registry(self):
        for destination in (self.registry.root, self.registry.root / "vault", self.registry.root.parent):
            with self.assertRaises(SkillError):
                export_vault(self.registry, project=self.project, destination=destination)

    def test_cli_creates_local_copy_using_explicit_destination(self):
        local = self.project / "local-copy-cli"
        out, err = io.StringIO(), io.StringIO()
        code = main(["--project", str(self.project), "export-obsidian", "--destination", str(local)], stdout=out, stderr=err)
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(Path(json.loads(out.getvalue())["vault_path"]), local)
        self.assertTrue((local / "Generated/Index.md").is_file())
