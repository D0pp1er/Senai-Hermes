"""Codex process execution, event streaming, and final-response capture."""

import subprocess
import json
import sys
import tempfile
from pathlib import Path

from .options import CodexOptions
from .workspace import resolve_output_path


def run_codex(prompt, project, *, options=None, stdout=None, stderr=None, session_callback=None):
    options = options or CodexOptions()
    session_args = options.session_args()
    destination = resolve_output_path(project, options.output_last_message) if options.output_last_message else None
    with tempfile.TemporaryDirectory(prefix='.senai-', dir=project) as temporary:
        output = Path(temporary) / 'response.txt'
        command = ['codex']
        if options.approval:
            command.extend(['--ask-for-approval', options.approval])
        command.append('exec')
        if options.sandbox is not None:
            command.extend(['--sandbox', options.sandbox])
        command.extend([
            '--cd', str(project), '--color', options.color,
            '--output-last-message', str(output),
        ])
        command.extend(options.to_args())
        if options.json or session_callback is not None:
            command.append('--json')
        command.extend(session_args)
        command.append('-')
        streams = {'stdout': stdout, 'stderr': stderr} if options.json else {'capture_output': True}
        try:
            if session_callback is None:
                result = subprocess.run(
                    command, cwd=project, input=prompt, text=True,
                    encoding='utf-8', errors='replace', check=False, **streams,
                )
            else:
                result = _run_session(command, project, prompt, session_callback,
                                      stdout if options.json else None,
                                      stderr if options.json else None,
                                      stream_json=options.json)
        except FileNotFoundError as exc:
            raise RuntimeError('Install Codex CLI and ensure codex is on PATH.') from exc
        if result.returncode:
            diagnostic = (result.stderr or '').strip() or (result.stdout or '').strip() or ('See streamed diagnostics above.' if options.json else 'No diagnostics.')
            if 'Not inside a trusted directory' in diagnostic:
                diagnostic += '\nUse --skip-git-repo-check for this folder, or run inside a trusted Git repository.'
            raise RuntimeError(f'Codex exited with code {result.returncode}: {diagnostic}')
        content = output.read_text(encoding='utf-8') if output.exists() else ''
        response = content.strip()
        if not response:
            raise RuntimeError('Codex returned no final response.')
        if destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding='utf-8')
        return response


def _run_session(command, project, prompt, callback, stdout, stderr, *, stream_json):
    """Observe native IDs while retaining JSON event delivery and final output capture."""
    # Files prevent pipe deadlocks for large prompts and stderr.
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as incoming, \
         tempfile.TemporaryFile(mode='w+', encoding='utf-8') as errors:
        incoming.write(prompt)
        incoming.seek(0)
        child = subprocess.Popen(command, cwd=project, stdin=incoming,
                                 stdout=subprocess.PIPE, stderr=errors, text=True,
                                 encoding='utf-8', errors='replace')
        try:
            for line in child.stdout:
                if stream_json:
                    target = stdout if stdout is not None else sys.stdout
                    target.write(line)
                    target.flush()
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get('type') == 'thread.started':
                    callback(event.get('thread_id'))
            code = child.wait()
        except BaseException:
            child.terminate()
            child.wait()
            raise
        finally:
            child.stdout.close()
        errors.seek(0)
        diagnostic = errors.read()
        if stream_json and diagnostic:
            target = stderr if stderr is not None else sys.stderr
            target.write(diagnostic)
            target.flush()
        return subprocess.CompletedProcess(command, code, stdout='', stderr=diagnostic)
