"""Execute one request through the existing senai CLI, with local result logs."""

import os
from pathlib import Path
import subprocess
import sys

from ..workspace import prepare_workspace


class CommandRunner:
    def __init__(self, project, state_dir, *, skip_git_repo_check=False, model=None, profile=None, search=False, skills=()):
        self.project = Path(project).expanduser().resolve()
        self.workspace = prepare_workspace(self.project)
        self.state_dir = Path(state_dir).resolve()
        if not self.state_dir.is_relative_to(self.workspace):
            raise ValueError('Telegram state must remain inside outputs/.')
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
        command = [sys.executable, '-m', 'senai', '--project', str(self.project), *self.flags, '--', job['prompt']]
        environment = {key: value for key, value in os.environ.items() if key not in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USER_IDS')}
        with stdout_path.open('w', encoding='utf-8') as stdout, stderr_path.open('w', encoding='utf-8') as stderr:
            result = subprocess.run(
                command, cwd=self.workspace, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, env=environment, check=False,
            )
        path = stdout_path if result.returncode == 0 else stderr_path
        with path.open(encoding='utf-8', errors='replace') as stream:
            text = stream.read(60001)
        if not text.strip():
            text = f'Local senai exited with code {result.returncode}. Inspect local logs in {directory}.'
        if len(text) > 60000:
            text = text[:60000] + f'\n[Reply truncated; complete local output: {path}]'
        return ('succeeded' if result.returncode == 0 else 'failed'), text.strip()
