import tempfile
import unittest
from pathlib import Path
from dataclasses import replace

from senai.memory import MemoryStore, Namespace
from senai.memory.candidates import extract_candidates, accept_candidate


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ns = Namespace(self.root, "team")
        self.store = MemoryStore(self.root / "memory.db")

    def propose(self, text="Memory: Invoices use PostgreSQL", **kwargs):
        return extract_candidates(text, namespace=self.ns, outcome_id="job:1",
                                  verified=True, **kwargs)

    def test_only_marked_verified_outcomes_propose_and_never_persist(self):
        self.assertEqual(extract_candidates("Memory: Fact", namespace=self.ns,
                         outcome_id="failed", verified=False), ())
        self.assertEqual(self.propose("ordinary result"), ())
        candidates = self.propose()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(self.store.list(self.ns), [])
        self.assertEqual(candidates[0].provenance, "outcome:job:1")

    def test_approval_namespace_delete_and_capacity(self):
        candidate = self.propose()[0]
        with self.assertRaises(ValueError):
            accept_candidate(self.store, self.ns, candidate, approved=False)
        with self.assertRaises(ValueError):
            accept_candidate(self.store, Namespace(self.root, "other"), candidate, approved=True)
        item = accept_candidate(self.store, self.ns, candidate, approved=True)
        self.assertEqual(item.text, candidate.text)
        self.store.delete(self.ns, item.id)
        self.assertEqual(self.store.retrieve(self.ns, "invoices"), [])
        with self.assertRaises(ValueError):
            accept_candidate(MemoryStore(self.root / "small.db", max_chars=5),
                             self.ns, candidate, approved=True)

    def test_secrets_duplicates_and_limits(self):
        result = self.propose("Memory: api_key=example\nMemory: Uses tabs\nMemory: Uses tabs")
        self.assertEqual([c.text for c in result], ["Uses tabs"])
        self.assertEqual(len(self.propose(
            "\n".join(f"Memory: Fact {i}" for i in range(8)), max_candidates=2)), 2)
        self.assertEqual(self.propose("Memory: " + "x" * 4001), ())
        with self.assertRaises(ValueError):
            self.propose("x" * 100001)
        candidate = self.propose()[0]
        with self.assertRaises(ValueError):
            accept_candidate(self.store, self.ns,
                             replace(candidate, text="password=example"), approved=True)

    def test_truthy_strings_do_not_count_as_verification_or_approval(self):
        with self.assertRaises(ValueError):
            extract_candidates("Memory: Fact", namespace=self.ns, outcome_id="job",
                               verified="false")
        with self.assertRaises(ValueError):
            accept_candidate(self.store, self.ns, self.propose()[0], approved="false")
