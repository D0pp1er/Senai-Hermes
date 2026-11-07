"""Codex process execution and final-response capture."""

import subprocess
import tempfile
from pathlib import Path

from .options import CodexOptions


def run_codex(prompt, project, *, options=None):
    options = options or CodexOptions()
    session_args = options.session_args()
    with tempfile.TemporaryDirectory(prefix='.senai-', dir=project) as temporary:
        output = Path(temporary) / 'response.txt'
        command = [
            'codex', 'exec', '--sandbox', 'workspace-write',
            '--cd', str(project), '--color', 'never',
            '--output-last-message', str(output),
        ]
        command.extend(options.to_args())
        command.extend(session_args)
        command.append('-')
        try:
            result = subprocess.run(
                command, cwd=project, input=prompt, capture_output=True, text=True,
                encoding='utf-8', errors='replace', check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError('Install Codex CLI and ensure codex is on PATH.') from exc
        if result.returncode:
            diagnostic = result.stderr.strip() or result.stdout.strip() or 'No diagnostics.'
            raise RuntimeError(f'Codex exited with code {result.returncode}: {diagnostic}')
        response = output.read_text(encoding='utf-8').strip() if output.exists() else ''
        if not response:
            raise RuntimeError('Codex returned no final response.')
        return response
