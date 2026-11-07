"""Native Codex execution with terminal streams preserved."""

import argparse
import subprocess
from pathlib import Path

from .workspace import prepare_workspace


def run_native(arguments, workspace, *, stdout=None, stderr=None):
    validate_native_args(arguments, workspace)
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


def validate_native_args(arguments, workspace):
    """Keep explicit workspace/output flags consistent with the outputs policy.

    This does not sandbox arbitrary tools or override native configuration.
    """
    workspace = Path(workspace).resolve()
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == '--':
            break
        flag = token.split('=', 1)[0]
        if flag in ('--cd', '--add-dir', '--worktree', '--remote') or token.startswith('-C'):
            raise ValueError(f'{flag} would relocate or expand the outputs/ workspace.')
        output_flags = ('--output-last-message', '--out', '--output', '-o')
        attached_short = token.startswith('-o') and not token.startswith('--') and token != '-o'
        if flag in output_flags or attached_short:
            if attached_short:
                value = token[2:]
            elif '=' in token:
                value = token.split('=', 1)[1]
            else:
                index += 1
                if index >= len(arguments):
                    raise ValueError(f'{flag} requires a path inside outputs/.')
                value = arguments[index]
            path = Path(value).expanduser()
            path = (workspace / path).resolve() if not path.is_absolute() else path.resolve()
            if not path.is_relative_to(workspace):
                raise ValueError(f'{flag} must write inside outputs/.')
        index += 1


def native_main(argv, stdout, stderr):
    parser = argparse.ArgumentParser(prog='senai codex', description='Forward native Codex commands inside outputs/. Put Codex arguments after --.')
    parser.add_argument('--project', default='.', help='Parent project directory.')
    parser.add_argument('arguments', nargs=argparse.REMAINDER, help='Native Codex arguments after --.')
    args = parser.parse_args(argv)
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    try:
        workspace = prepare_workspace(args.project)
        return run_native(arguments, workspace, stdout=stdout, stderr=stderr)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'senai: {exc}', file=stderr)
        return 2
    except KeyboardInterrupt:
        return 130
