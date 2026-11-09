"""Codex CLI wrapper: write/edit requests, interactive work, and native commands."""

import argparse
import os
import sys
from pathlib import Path

from .codex import run_codex
from .exec_flags import add_exec_flags, collect_exec_args
from .options import CodexOptions
from .native import chat_main, native_main, review_main, run_native
from .prompts import build_prompt
from .workspace import prepare_workspace, resolve_output_path


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, allow_abbrev=False,
        epilog='Use senai chat for interactive Codex, senai review for code review, senai telegram for bot control, senai memory for profiles, senai cron for schedules, or senai codex -- <args> for native commands.',
    )
    parser.add_argument('request', nargs='?', help='Quoted request, or - to read stdin.')
    parser.add_argument('--project', '-C', '--cd', default='.', help='Parent project directory; code goes in its outputs/ folder.')
    parser.add_argument('--installation', default=os.environ.get('SENAI_INSTALLATION_ROOT'), help='Explicit single-owner memory installation root; defaults to SENAI_INSTALLATION_ROOT.')
    parser.add_argument('-m', '--model', help='Codex model override.')
    parser.add_argument('-p', '--profile', help='Codex configuration profile.')
    parser.add_argument('-c', '--config', action='append', default=[], metavar='KEY=VALUE', help='Repeatable Codex configuration override.')
    parser.add_argument('-i', '--image', action='append', default=[], metavar='FILE', help='Attach an image (repeatable).')
    parser.add_argument('--search', action='store_true', help='Enable live Codex web search.')
    parser.add_argument('--skill', action='append', default=[], metavar='NAME', help='Mention an installed Codex skill (repeatable).')
    sessions = parser.add_mutually_exclusive_group()
    sessions.add_argument('--resume', metavar='SESSION', help='Continue a saved Codex session by id or name.')
    sessions.add_argument('--last', action='store_true', help='Continue the latest Codex session in outputs/.')
    parser.add_argument('--skip-git-repo-check', action='store_true', help='Allow execution outside a Git repository, as in Codex exec.')
    add_exec_flags(parser)
    return parser


def main(argv=None, stdout=None, stderr=None, stdin=None):
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    stdin = stdin if stdin is not None else sys.stdin
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'cron':
        from contextlib import redirect_stdout, redirect_stderr
        from .cron_runtime import manage_cli as cron_main
        with redirect_stdout(stdout), redirect_stderr(stderr):
            return cron_main(argv[1:])
    if argv and argv[0] == 'memory':
        from contextlib import redirect_stdout, redirect_stderr
        from .memory.__main__ import main as memory_main
        arguments = argv[1:]
        if '--installation' not in arguments and '--project' not in arguments:
            root = os.environ.get('SENAI_INSTALLATION_ROOT')
            if root:
                arguments = ['--installation', root, *arguments]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            return memory_main(arguments)
    if argv and argv[0] == 'telegram':
        from .telegram.cli import telegram_main
        return telegram_main(argv[1:], stdout, stderr)
    routes = {'review': review_main, 'codex': native_main, 'chat': chat_main}
    if argv and argv[0] in routes:
        return routes[argv[0]](argv[1:], stdout, stderr)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.version:
            return run_native(['--version'], Path.cwd(), stdout=stdout, stderr=stderr)
        if args.worktree or args.add_dir:
            raise ValueError('--worktree/--add-dir conflict with the outputs/ workspace policy.')
        if args.approve_for_me and args.ask_for_approval:
            raise ValueError('--approve-for-me cannot be combined with --ask-for-approval.')
        if args.request is None and stdin.isatty():
            parser.error('a request is required; quote it or pipe it through stdin')
        request = stdin.read() if args.request in (None, '-') else args.request
        prompt = build_prompt(request, skills=tuple(args.skill))
        images = tuple(str(Path(image).expanduser().resolve()) for image in args.image)
        for image in images:
            if not Path(image).is_file():
                raise ValueError(f'Image must be an existing file: {image}')
        if args.output_schema:
            schema = Path(args.output_schema).expanduser().resolve()
            if not schema.is_file():
                raise ValueError(f'Output schema must be an existing file: {schema}')
            args.output_schema = str(schema)
        workspace = prepare_workspace(args.project)
        destination = str(resolve_output_path(workspace, args.output_last_message)) if args.output_last_message else None
        sandbox = None if args.approve_for_me or args.dangerously_bypass_approvals_and_sandbox else (args.sandbox or 'workspace-write')
        options = CodexOptions(
            model=args.model, profile=args.profile, config=tuple(args.config), images=images,
            search=args.search, resume=args.resume, last=args.last,
            skip_git_repo_check=args.skip_git_repo_check, extra_args=collect_exec_args(args),
            sandbox=sandbox, color=args.color, approval=args.ask_for_approval,
            output_last_message=destination, json=args.json,
        )
        streams = {'stdout': stdout, 'stderr': stderr} if options.json else {}
        if args.installation:
            from .memory_runtime import InstallationRuntime
            confirmation = None
            if stdin.isatty() and not options.json:
                def confirmation(event):
                    print("Save this " + event.kind + " in USER.md? " + event.text +
                          " [y/N]: ", file=stderr, end="", flush=True)
                    return stdin.readline().strip().lower() in ("y", "yes")
            response = InstallationRuntime(args.installation).execute(
                request, workspace, executor=run_codex, options=options,
                skills=tuple(args.skill), confirmation=confirmation, **streams)
        else:
            response = run_codex(prompt, workspace, options=options, **streams)
        if not options.json:
            print(response, file=stdout)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'senai: {exc}', file=stderr)
        return 2
    except KeyboardInterrupt:
        print('senai: Interrupted.', file=stderr)
        return 130
