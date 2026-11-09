from dataclasses import replace
import unittest

from senai.memory import MemoryEvent, evaluate_noteworthy


class NoteworthyTests(unittest.TestCase):
    def event(self, **kwargs):
        defaults = dict(event_id="event-1", kind="preference", text="Prefers concise replies",
                        source="user", verified=True)
        defaults.update(kwargs)
        return MemoryEvent(**defaults)

    def test_repetition_does_not_replace_explicit_confirmation(self):
        events = [self.event(event_id=f"event-{i}") for i in range(10)]
        self.assertEqual(evaluate_noteworthy(events), ())
        confirmed = self.event(confirmed=True)
        proposal, = evaluate_noteworthy([confirmed])
        self.assertEqual(proposal.name, "USER.md")
        self.assertEqual(proposal.text, confirmed.text)
        self.assertTrue(proposal.noteworthy)
        self.assertTrue(proposal.verified)
        self.assertEqual(proposal.evidence_id, confirmed.event_id)

    def test_user_categories_require_user_source_verified_confirmation(self):
        for kind in ("preference", "habit", "like", "dislike", "choice"):
            with self.subTest(kind=kind):
                event = self.event(kind=kind, confirmed=True, significant=True)
                self.assertEqual(len(evaluate_noteworthy([event])), 1)
                for change in ({"confirmed": False}, {"verified": False},
                               {"source": "model"}, {"source": "validator"}):
                    self.assertEqual(evaluate_noteworthy([replace(event, **change)]), ())
        self.assertEqual(evaluate_noteworthy([
            self.event(kind="choice", confirmed=True, significant=False)]), ())

    def test_only_verified_significant_validator_milestones(self):
        event = self.event(kind="milestone", text="Completed the first release",
                           source="validator", significant=True)
        proposal, = evaluate_noteworthy([event])
        self.assertEqual(proposal.name, "MEMORY.md")
        for change in ({"verified": False}, {"significant": False},
                       {"source": "model"}, {"source": "user"}):
            self.assertEqual(evaluate_noteworthy([replace(event, **change)]), ())
        self.assertEqual(evaluate_noteworthy([self.event(kind="ordinary")]), ())

    def test_secret_logs_empty_and_long_candidates_are_not_proposed(self):
        for text in ("api_key=example", "password=example", "Bearer example",
                     "line one\nline two", "", "x" * 241):
            with self.subTest(text=text):
                self.assertEqual(evaluate_noteworthy([
                    self.event(text=text, confirmed=True)]), ())

    def test_existing_and_batch_duplicate_facts_are_skipped(self):
        events = [self.event(confirmed=True), self.event(
            event_id="event-2", text="  PREFERS   concise replies. ", confirmed=True)]
        self.assertEqual(len(evaluate_noteworthy(events)), 1)
        existing = {"USER.md": "- Prefers concise replies.\n\n- Likes Python"}
        self.assertEqual(evaluate_noteworthy(events, existing=existing), ())
        self.assertEqual(len(evaluate_noteworthy(events,
                         existing={"MEMORY.md": "Prefers concise replies"})), 1)

    def test_replayed_event_id_is_not_counted_twice(self):
        one = self.event(confirmed=True)
        two = self.event(text="Likes Python", confirmed=True)
        self.assertEqual(len(evaluate_noteworthy([one, two])), 1)

    def test_candidate_and_text_budgets_are_deterministic(self):
        events = [self.event(event_id=f"e-{i}", text=f"Likes option {i}",
                             confirmed=True) for i in range(10)]
        self.assertEqual(len(evaluate_noteworthy(events, max_candidates=2)), 2)
        self.assertLessEqual(sum(len(p.text) for p in evaluate_noteworthy(
            events, max_chars=30)), 30)
        self.assertEqual(evaluate_noteworthy(events, max_chars=0), ())
        self.assertEqual(evaluate_noteworthy(events, max_candidates=0), ())

    def test_invalid_decision_types_and_batch_limits_fail_without_echo(self):
        for change in ({"confirmed": "yes"}, {"verified": 1}, {"significant": None}):
            with self.assertRaises(ValueError):
                evaluate_noteworthy([self.event(**change)])
        with self.assertRaises(ValueError):
            evaluate_noteworthy([self.event(event_id="password=example")])
        with self.assertRaises(ValueError):
            evaluate_noteworthy([self.event()] * 101)
        with self.assertRaises(ValueError):
            evaluate_noteworthy([{"text": "fake event"}])
        for kwargs in ({"max_candidates": -1}, {"max_candidates": True},
                       {"max_chars": -1}, {"max_chars": True}):
            with self.assertRaises(ValueError):
                evaluate_noteworthy([], **kwargs)

    def test_evaluation_does_not_modify_evidence_or_existing_memory(self):
        event = self.event(confirmed=True)
        existing = {"USER.md": "- Likes Python"}
        before = dict(existing)
        evaluate_noteworthy([event], existing=existing)
        self.assertEqual(existing, before)
        self.assertEqual(event.text, "Prefers concise replies")

    def test_full_target_preserves_existing_content(self):
        existing = {"USER.md": "x" * 3990}
        self.assertEqual(evaluate_noteworthy([
            self.event(confirmed=True)], existing=existing), ())
        self.assertEqual(existing["USER.md"], "x" * 3990)

    def test_cli_dry_run_never_saves_and_filters_unconfirmed_preferences(self):
        import json
        from dataclasses import asdict
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events = root / "events.json"
            events.write_text(json.dumps([
                asdict(self.event(confirmed=False)),
                asdict(self.event(event_id="e2", kind="milestone", source="validator",
                                  text="Completed first release", significant=True))]))
            result = subprocess.run([
                sys.executable, "-m", "senai.memory", "--installation", str(root),
                "evaluate-events", str(events)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            proposals = json.loads(result.stdout)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0]["name"], "MEMORY.md")
            self.assertFalse((root / "outputs/.senai-memory/MEMORY.md").exists())
            self.assertFalse((root / "outputs/.senai-memory/USER.md").exists())
            events.write_text("x" * 100001)
            failed = subprocess.run([
                sys.executable, "-m", "senai.memory", "--installation", str(root),
                "evaluate-events", str(events)], text=True, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)

    def test_proposals_adapt_to_integrated_learning_callback(self):
        import tempfile
        from pathlib import Path
        from senai.memory_runtime import InstallationRuntime, LearningDecision
        with tempfile.TemporaryDirectory() as temporary:
            runtime = InstallationRuntime(temporary)
            workspace = Path(temporary) / "task"
            workspace.mkdir()
            event = self.event(confirmed=True)
            def learning(request, response, workspace):
                return [LearningDecision(p.name, p.text, noteworthy=p.noteworthy,
                                         verified=p.verified, confirmed=event.confirmed,
                                         kind=event.kind, source=event.source,
                                         significant=event.significant)
                        for p in evaluate_noteworthy([event])]
            def executor(prompt, workspace, session_callback, **kwargs):
                session_callback("126f40f5-325d-440e-ab17-fd4689193aee")
                return "done"
            response = runtime.execute("Build an invoice", workspace,
                                       executor=executor, learning=learning)
            self.assertEqual(response, "done")
            self.assertIn(event.text, runtime.memory.profiles.read("USER.md").text)
            self.assertEqual(runtime.memory.profiles.read("SOUL.md").text, "")

    def test_failed_execution_never_invokes_evaluator_or_saves(self):
        import tempfile
        from pathlib import Path
        from senai.memory_runtime import InstallationRuntime
        with tempfile.TemporaryDirectory() as temporary:
            runtime = InstallationRuntime(temporary)
            def executor(*args, **kwargs):
                raise RuntimeError("fixture failed")
            def learning(*args):
                self.fail("must not evaluate failed execution")
            with self.assertRaises(RuntimeError):
                runtime.execute("Build an invoice", Path(temporary),
                                executor=executor, learning=learning)
            self.assertEqual(runtime.memory.profiles.read("USER.md").text, "")
