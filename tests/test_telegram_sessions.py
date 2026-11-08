import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai.telegram.runner import CommandRunner
from senai.telegram.store import JobStore

SID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


class SharedSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / 'outputs/state'
        self.store = JobStore(self.state / 'state.sqlite3')

    def test_shared_session_survives_store_restart(self):
        self.store.bind_shared_session(SID)
        self.assertEqual(JobStore(self.store.path).shared_session(), SID)

    def test_binding_another_session_cannot_silently_replace_the_shared_chat(self):
        self.store.bind_shared_session(SID)
        with self.assertRaises(ValueError):
            self.store.bind_shared_session(OTHER)
        self.assertEqual(self.store.shared_session(), SID)

    def test_first_turn_saves_id_and_other_user_resumes_exactly_that_id(self):
        seen = []
        def execute(command, **kwargs):
            seen.append(command)
            kwargs['stdout'].write(json.dumps({'type': 'thread.started', 'thread_id': SID}) + '\n')
            Path(command[command.index('--output-last-message') + 1]).write_text('Remembered')
            return subprocess.CompletedProcess(command, 0)
        with patch('senai.telegram.runner.subprocess.run', side_effect=execute):
            runner = CommandRunner(self.root, self.state, store=self.store)
            self.assertEqual(runner({'id': 1, 'chat_id': 7, 'user_id': 7, 'prompt': 'Remember marker'})[0], 'succeeded')
            restarted = CommandRunner(self.root, self.state, store=JobStore(self.store.path))
            self.assertEqual(restarted({'id': 2, 'chat_id': 8, 'user_id': 8, 'prompt': 'Recall marker'})[0], 'succeeded')
        self.assertNotIn('--resume', seen[0])
        self.assertEqual(seen[1][seen[1].index('--resume') + 1], SID)
        self.assertNotIn('--last', seen[1])

    def test_missing_new_thread_id_does_not_silently_fall_back_to_one_off(self):
        def execute(command, **kwargs):
            Path(command[command.index('--output-last-message') + 1]).write_text('Done')
            return subprocess.CompletedProcess(command, 0)
        with patch('senai.telegram.runner.subprocess.run', side_effect=execute):
            status, result = CommandRunner(self.root, self.state, store=self.store)({'id': 1, 'prompt': 'Write code'})
        self.assertEqual(status, 'failed')
        self.assertIn('session', result.lower())
        self.assertIsNone(self.store.shared_session())

    def test_failed_resume_keeps_saved_session_instead_of_creating_another(self):
        self.store.bind_shared_session(SID)
        def execute(command, **kwargs):
            kwargs['stderr'].write('Session unavailable')
            return subprocess.CompletedProcess(command, 2)
        with patch('senai.telegram.runner.subprocess.run', side_effect=execute):
            status, _ = CommandRunner(self.root, self.state, store=self.store)({'id': 1, 'prompt': 'Continue'})
        self.assertEqual(status, 'failed')
        self.assertEqual(self.store.shared_session(), SID)

    def test_recovery_reads_id_from_interrupted_job_events(self):
        self.store.consume(1, {'chat_id': 7, 'user_id': 7, 'prompt': 'Write code'})
        self.store.claim_next()
        directory = self.state / 'jobs/1'
        directory.mkdir(parents=True)
        (directory / 'stdout.txt').write_text(json.dumps({'type': 'thread.started', 'thread_id': SID}) + '\n')
        CommandRunner(self.root, self.state, store=self.store).recover_session()
        self.assertEqual(self.store.shared_session(), SID)
