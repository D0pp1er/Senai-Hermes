import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_fresh_process_crud_context_and_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def run(*args, scope="team"):
                return subprocess.run(
                    [sys.executable, "-m", "senai.memory", "--project", str(root),
                     "--scope", scope, *args], text=True, capture_output=True)
            added = run("add", "Invoices use PostgreSQL", "--provenance", "manual")
            self.assertEqual(added.returncode, 0, added.stderr)
            entry_id = json.loads(added.stdout)["id"]
            self.assertEqual(len(json.loads(run("list").stdout)), 1)
            self.assertEqual(json.loads(run("list", scope="other").stdout), [])
            self.assertIn("PostgreSQL", run("context", "invoices").stdout)
            self.assertEqual(run("update", entry_id, "Invoices use SQLite",
                                 "--provenance", "manual").returncode, 0)
            self.assertIn("SQLite", run("context", "invoices").stdout)
            self.assertEqual(run("delete", entry_id).returncode, 0)
            self.assertEqual(json.loads(run("list").stdout), [])
            self.assertTrue((root / "outputs" / ".senai-memory" / "memory.db").is_file())
            failure = run("add", "api_key=example", "--provenance", "manual")
            self.assertNotEqual(failure.returncode, 0)
            self.assertNotIn("example", failure.stderr)

    def test_missing_scope_fails_and_symlinked_outputs_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "outside").mkdir()
            (root / "outputs").symlink_to(root / "outside", target_is_directory=True)
            result = subprocess.run(
                [sys.executable, "-m", "senai.memory", "--project", str(root),
                 "--scope", "team", "list"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list((root / "outside").iterdir()), [])
