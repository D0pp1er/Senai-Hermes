"""Codex process execution, event streaming, and final-response capture."""

import subprocess
import tempfile
from pathlib import Path

from .options import CodexOptions
from .workspace import resolve_output_path


def run_codex(prompt, project, *, options=None, stdout=None, stderr=None):
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
        if options.json:
            command.append('--json')
        command.extend(session_args)
        command.append('-')
        streams = {'stdout': stdout, 'stderr': stderr} if options.json else {'capture_output': True}
        try:
            result = subprocess.run(
                command, cwd=project, input=prompt, text=True,
                encoding='utf-8', errors='replace', check=False, **streams,
            )
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
