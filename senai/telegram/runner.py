"""Execute one request through the existing senai CLI, with local result logs."""

import os
import json
import uuid
from pathlib import Path
import subprocess
import sys

from ..workspace import prepare_workspace
from .store import JobStore


class CommandRunner:
    def __init__(self, project, state_dir, *, store=None, skip_git_repo_check=False, model=None, profile=None, search=False, skills=()):
        self.project = Path(project).expanduser().resolve()
        self.workspace = prepare_workspace(self.project)
        self.state_dir = Path(state_dir).resolve()
        if not self.state_dir.is_relative_to(self.workspace):
            raise ValueError('Telegram state must remain inside outputs/.')
        self.store = store or JobStore(self.state_dir / 'state.sqlite3')
        self.flags = ['--ask-for-approval', 'never']
        if skip_git_repo_check:
            self.flags.append('--skip-git-repo-check')
        if model:
            self.flags.extend(['--model', model])
        if profile:
            self.flags.extend(['--profile', profile])
        if search:
            self.flags.append('--search')
        for skill in skills:
            self.flags.extend(['--skill', skill])

    def __call__(self, job):
        directory = self.state_dir / 'jobs' / str(job['id'])
        directory.mkdir(parents=True, exist_ok=False)
        directory.chmod(0o700)
        stdout_path, stderr_path = directory / 'stdout.txt', directory / 'stderr.txt'
        response_path = directory / 'response.txt'
        session_id = self.store.shared_session()
        resume = ['--resume', session_id] if session_id else []
        command = [sys.executable, '-m', 'senai', '--project', str(self.project), *self.flags, '--json', '--output-last-message', str(response_path), *resume, '--', job['prompt']]
        environment = {key: value for key, value in os.environ.items() if key not in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USER_IDS')}
        with stdout_path.open('w', encoding='utf-8') as stdout, stderr_path.open('w', encoding='utf-8') as stderr:
            result = subprocess.run(
                command, cwd=self.workspace, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, env=environment, check=False,
            )
        emitted_session = session_from_events(stdout_path)
        if emitted_session:
            try:
                self.store.bind_shared_session(emitted_session, job['id'])
            except ValueError as error:
                return 'failed', str(error)
        if result.returncode == 0 and not (session_id or emitted_session):
            return 'failed', 'No verified Codex session ID was captured. Inspect local job logs; this request will not be silently repeated as a one-off.'
        path = response_path if result.returncode == 0 else stderr_path
        if not path.is_file():
            return 'failed', 'Codex returned no saved response. The shared session, if captured, was retained.'
        with path.open(encoding='utf-8', errors='replace') as stream:
            text = stream.read(60001)
        if not text.strip():
            text = f'Local senai exited with code {result.returncode}. Inspect local logs in {directory}.'
        if len(text) > 60000:
            text = text[:60000] + f'\n[Reply truncated; complete local output: {path}]'
        return ('succeeded' if result.returncode == 0 else 'failed'), text.strip()

    def recover_session(self):
        if self.store.shared_session():
            return
        for job in self.store.unbound_running_jobs():
            session_id = session_from_events(self.state_dir / 'jobs' / str(job['id']) / 'stdout.txt')
            if session_id:
                self.store.bind_shared_session(session_id, job['id'])
                return


def session_from_events(path):
    if not path.is_file():
        return None
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            try:
                event = json.loads(line)
                if isinstance(event, dict) and event.get('type') == 'thread.started':
                    return str(uuid.UUID(event['thread_id']))
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
    return None
