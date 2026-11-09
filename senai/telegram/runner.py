"""Execute one request through the existing senai CLI, with local result logs."""

import os
import json
import uuid
from pathlib import Path
import subprocess
import sys

from ..workspace import prepare_workspace
from .store import JobStore
from .chat import chat_request
from .speech import SpeechError
from ..processes import run_bounded, ExecutionUncertain
import math


class CommandRunner:
    def __init__(self, project, state_dir, *, store=None, skip_git_repo_check=False, model=None, profile=None, search=False, skills=(), chat_style=False, media=None, speech=None, execution_timeout=None, installation=None):
        self.project = Path(project).expanduser().resolve()
        self.workspace = prepare_workspace(self.project)
        self.state_dir = Path(state_dir).resolve()
        if not self.state_dir.is_relative_to(self.workspace):
            raise ValueError('Telegram state must remain inside outputs/.')
        self.store = store or JobStore(self.state_dir / 'state.sqlite3')
        if execution_timeout is not None and (isinstance(execution_timeout, bool) or not math.isfinite(execution_timeout) or not 0 < execution_timeout <= 3600):
            raise ValueError('Execution timeout must be positive and at most 3600 seconds.')
        self.execution_timeout = execution_timeout
        self.speech = speech
        self.media = media
        self.chat_style = chat_style
        self.flags = ['--ask-for-approval', 'never']
        # None preserves shared child-CLI defaults. An explicit startup value pins
        # the installation; empty string pins the absence of memory configuration.
        self.installation = None
        if installation is not None:
            self.installation = str(Path(installation).expanduser().resolve()) if str(installation) else ''
            if self.installation and not Path(self.installation).is_dir():
                raise ValueError('Configured memory installation must be an existing directory.')
            self.flags.extend(['--installation', self.installation])
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
        mode = self.media.voice_mode(job) if self.media is not None else None
        voice = mode is not None
        if mode == 'reuse':
            text = job['prompt']
            response_path.write_text(text, encoding='utf-8')
            return 'succeeded', self._prepare_voice(job, text)
        session_id = self.store.shared_session()
        resume = ['--resume', session_id] if session_id else []
        prompt = job['prompt']
        if self.chat_style:
            prompt = chat_request(prompt, attachment_manifest=directory / 'attachments.json' if self.media is not None else None, voice_reply=voice)
        command = [sys.executable, '-m', 'senai', '--project', str(self.project), *self.flags, '--json', '--output-last-message', str(response_path), *resume, '--', prompt]
        environment = {key: value for key, value in os.environ.items() if key not in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USER_IDS', 'SENAI_TTS_API_KEY')}
        uncertain = None
        with stdout_path.open('w', encoding='utf-8') as stdout, stderr_path.open('w', encoding='utf-8') as stderr:
            if self.execution_timeout is None:
                result = subprocess.run(
                    command, cwd=self.workspace, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, env=environment, check=False,
                )
            else:
                try:
                    result = run_bounded(command, cwd=self.workspace, stdout=stdout,
                                         stderr=stderr, env=environment,
                                         timeout=self.execution_timeout)
                except ExecutionUncertain as error:
                    uncertain = error
                    result = subprocess.CompletedProcess(command, 124)
        emitted_session = session_from_events(stdout_path)
        if emitted_session:
            try:
                self.store.bind_shared_session(emitted_session, job['id'])
            except ValueError as error:
                if uncertain is not None:
                    raise uncertain
                return 'failed', str(error)
        if uncertain is not None:
            raise uncertain
        if result.returncode == 0 and not (session_id or emitted_session):
            return 'failed', 'No verified Codex session ID was captured. Inspect local job logs; this request will not be silently repeated as a one-off.'
        path = response_path if result.returncode == 0 else stderr_path
        if not path.is_file():
            return 'failed', 'Codex returned no saved response. The shared session, if captured, was retained.'
        with path.open(encoding='utf-8', errors='replace') as stream:
            text = stream.read(60001)
        if not text.strip():
            text = (f'The request could not produce a reply (exit code {result.returncode}). Please ask the bot operator to check the server logs.'
                    if self.chat_style else f'Local senai exited with code {result.returncode}. Inspect local logs in {directory}.')
        if len(text) > 60000:
            suffix = ('\n[Reply shortened. Ask for the specific part you need.]' if self.chat_style
                      else f'\n[Reply truncated; complete local output: {path}]')
            text = text[:60000] + suffix
        if result.returncode == 0 and self.media is not None:
            try:
                self.media.prepare(job['id'], directory / 'attachments.json')
            except (ValueError, OSError, TypeError):
                text += '\nI could not attach the selected images. Please request a PNG or JPEG from the workspace.'
        if result.returncode == 0 and voice:
            text = self._prepare_voice(job, text.strip())
        return ('succeeded' if result.returncode == 0 else 'failed'), text.strip()

    def _prepare_voice(self, job, text):
        if self.speech is None or self.media is None:
            return text + '\nVoice replies are not configured; here is the text answer.'
        try:
            self.media.add_voice(job['id'], self.speech(text))
        except (SpeechError, ValueError, OSError):
            return text + '\nI could not generate the voice reply. The text answer is above.'
        return text

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
