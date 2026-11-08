import concurrent.futures
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from senai.memory import MemoryStore, Namespace


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "memory.db"
        self.ns = Namespace(self.root / "project", "team")
        self.store = MemoryStore(self.path)

    def test_restart_retrieval_and_scope_isolation(self):
        entry = self.store.add(self.ns, "Use PostgreSQL for invoices", provenance="user:1")
        code = ("from senai.memory import MemoryStore, Namespace; "
                "import sys; s=MemoryStore(sys.argv[1]); "
                "print(s.retrieve(Namespace(sys.argv[2], 'team'), 'invoices')[0].id)")
        result = subprocess.check_output(
            [sys.executable, "-c", code, str(self.path), self.ns.project], text=True)
        self.assertEqual(result.strip(), entry.id)
        self.assertEqual(self.store.list(Namespace(self.root / "other", "team")), [])
        self.assertEqual(self.store.list(Namespace(self.root / "project", "private")), [])

    def test_crud_and_metadata(self):
        item = self.store.add(self.ns, "Use tabs", provenance="user:42")
        self.assertTrue(item.id)
        self.assertEqual(item.provenance, "user:42")
        self.assertTrue(item.created_at)
        updated = self.store.update(self.ns, item.id, "Use spaces", provenance="user:43")
        self.assertEqual(updated.created_at, item.created_at)
        self.assertGreaterEqual(updated.updated_at, item.updated_at)
        self.assertEqual(updated.text, "Use spaces")
        with self.assertRaises(KeyError):
            self.store.update(Namespace(self.root / "other", "team"), item.id,
                              "Wrong", provenance="user:1")
        self.assertFalse(self.store.delete(Namespace(self.root / "other", "team"), item.id))
        self.assertTrue(self.store.delete(self.ns, item.id))
        self.assertEqual(self.store.retrieve(self.ns, "spaces"), [])

    def test_capacity_update_rollback_and_duplicate(self):
        store = MemoryStore(self.path, max_entries=2, max_chars=20)
        item = store.add(self.ns, "Use tabs", provenance="user")
        with self.assertRaises(ValueError):
            store.add(self.ns, "Use tabs", provenance="user")
        with self.assertRaises(ValueError):
            store.update(self.ns, item.id, "x" * 21, provenance="user")
        self.assertEqual(store.list(self.ns)[0].text, "Use tabs")
        store.add(self.ns, "Use SQLite", provenance="user")
        with self.assertRaises(ValueError):
            store.add(self.ns, "X", provenance="user")

    def test_validation_and_secrets(self):
        for text in ("", "  ", "api_key=secret-example", "password: example",
                     "Bearer abcdefghijk", "-----BEGIN PRIVATE KEY-----"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.store.add(self.ns, text, provenance="user")
        with self.assertRaises(ValueError):
            self.store.add(self.ns, "valid fact", provenance="")
        with self.assertRaises(ValueError):
            Namespace(self.root, "")

    def test_corrupt_database_is_not_replaced(self):
        corrupt = self.root / "corrupt.db"
        corrupt.write_bytes(b"not a sqlite database")
        with self.assertRaises(sqlite3.DatabaseError):
            MemoryStore(corrupt)
        self.assertEqual(corrupt.read_bytes(), b"not a sqlite database")

    def test_concurrent_capacity_is_atomic(self):
        def write(i):
            try:
                return MemoryStore(self.path, max_entries=5).add(
                    self.ns, f"Fact number {i}", provenance="test").id
            except ValueError:
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(write, range(20)))
        self.assertEqual(sum(x is not None for x in results), 5)
        self.assertEqual(len(self.store.list(self.ns)), 5)

    def test_canonical_project_alias(self):
        self.assertEqual(self.ns, Namespace(self.root / "project" / ".." / "project", "team"))
