import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/check_workstream_scope.py'


class ScopeGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.env = dict(os.environ, GIT_AUTHOR_NAME='Scope QA', GIT_COMMITTER_NAME='Scope QA', GIT_AUTHOR_EMAIL='scope@example.invalid', GIT_COMMITTER_EMAIL='scope@example.invalid')
        self.git('init', '-b', 'main')
        policy = {'version': 1, 'coordinator_paths': ['AGENTS.md', 'projectprogress/parallel/ownership.json'], 'workstreams': {'memory': {'branch': 'feature/memory', 'prefixes': ['senai/memory/', 'tests/memory/', 'projectprogress/workstreams/memory/'], 'files': ['requirements-memory.txt']}}}
        self.write('projectprogress/parallel/ownership.json', json.dumps(policy))
        self.write('AGENTS.md', 'shared rules v1')
        self.write('senai/codex.py', 'shared implementation')
        self.write('senai/memory/existing.py', 'owned implementation')
        self.write('.gitignore', 'outputs/\n')
        self.write('projectprogress/workstreams/memory/delivery.json', json.dumps({'schema_version': 1, 'feature': 'memory', 'status': 'draft'}))
        self.git('add', '.')
        self.git('commit', '-m', 'baseline')
        self.git('switch', '-c', 'feature/memory')

    def git(self, *arguments):
        return subprocess.run(['git', *arguments], cwd=self.repo, env=self.env, check=True, text=True, capture_output=True)

    def write(self, name, value):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def check(self, *extra):
        return subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.repo), '--feature', 'memory', *extra], text=True, capture_output=True)

    def test_owned_committed_staged_and_untracked_paths_pass(self):
        self.write('senai/memory/new.py', 'owned')
        self.git('add', 'senai/memory/new.py')
        self.git('commit', '-m', 'owned')
        self.write('tests/memory/test_new.py', 'owned staged')
        self.git('add', 'tests/memory/test_new.py')
        self.write('requirements-memory.txt', 'owned untracked')
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_runtime_change_fails(self):
        self.write('senai/codex.py', 'changed core')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('senai/codex.py', result.stdout)

    def test_rename_does_not_hide_shared_source_deletion(self):
        self.git('mv', 'senai/codex.py', 'senai/memory/copied.py')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('senai/codex.py', result.stdout)

    def test_untracked_other_feature_file_fails(self):
        self.write('senai/cron/new.py', 'not owned')
        self.assertEqual(self.check().returncode, 1)

    def test_ignored_outputs_are_not_scope_violations(self):
        self.write('outputs/qa/result.txt', 'artifact')
        self.assertEqual(self.check().returncode, 0)

    def test_matching_coordinator_update_is_allowed_but_drift_is_not(self):
        self.git('switch', 'main')
        self.write('AGENTS.md', 'shared rules v2')
        self.git('add', 'AGENTS.md')
        self.git('commit', '-m', 'coordinator update')
        self.git('switch', 'feature/memory')
        self.write('AGENTS.md', 'shared rules v2')
        self.assertEqual(self.check().returncode, 0)
        self.write('AGENTS.md', 'unauthorized policy change')
        self.assertEqual(self.check().returncode, 1)

    def test_wrong_branch_is_rejected(self):
        self.git('switch', 'main')
        self.assertEqual(self.check().returncode, 2)

    def test_draft_is_not_ready_for_merge(self):
        result = self.check('--ready')
        self.assertEqual(result.returncode, 1)
        self.assertIn('draft', result.stdout.lower())

    def test_ready_manifest_requires_evidence_and_contract(self):
        self.write('projectprogress/workstreams/memory/delivery.json', json.dumps({'schema_version': 1, 'feature': 'memory', 'status': 'ready'}))
        self.assertEqual(self.check('--ready').returncode, 1)

    def test_complete_ready_contract_passes(self):
        manifest = {'schema_version': 1, 'feature': 'memory', 'status': 'ready', 'modules': ['senai.memory'], 'public_api': [{'name': 'MemoryStore', 'signature': 'MemoryStore(path)', 'purpose': 'Scoped durable memory'}], 'commands': ['python -m senai.memory --help'], 'executor_contract': {'interface': 'injected callback', 'inputs': ['prompt', 'scope'], 'outputs': ['response']}, 'dependencies': {'runtime': [], 'development': []}, 'storage': {'namespace': 'outputs/.memory', 'schema_version': 1, 'migration_notes': 'New isolated store; no old rows removed.'}, 'verification': {'offline_commands': ['python -m unittest'], 'offline_result': 'passed', 'offline_test_count': 1, 'tested_commit': self.git('rev-parse', 'HEAD').stdout.strip()}, 'integration': {'shared_file_changes': [], 'sibling_requirements': []}, 'limitations': ['fixture only']}
        self.write('projectprogress/workstreams/memory/delivery.json', json.dumps(manifest))
        result = self.check('--ready')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
