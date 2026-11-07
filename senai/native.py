"""Native Codex execution with terminal streams preserved."""

import argparse
import subprocess

from .workspace import prepare_workspace


def run_native(arguments, workspace, *, stdout=None, stderr=None):
    command = ['codex', '--sandbox', 'workspace-write', '--cd', str(workspace), *arguments]
    try:
        result = subprocess.run(command, cwd=workspace, stdout=stdout, stderr=stderr, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError('Install Codex CLI and ensure codex is on PATH.') from exc
    return result.returncode


def chat_main(argv, stdout, stderr):
    parser = argparse.ArgumentParser(prog='senai chat', description='Start interactive Codex inside outputs/. Use /skills in the terminal.')
    parser.add_argument('--project', default='.', help='Parent project directory.')
    args = parser.parse_args(argv)
    try:
        workspace = prepare_workspace(args.project)
        return run_native(['--no-alt-screen'], workspace, stdout=stdout, stderr=stderr)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'senai: {exc}', file=stderr)
        return 2
    except KeyboardInterrupt:
        return 130
