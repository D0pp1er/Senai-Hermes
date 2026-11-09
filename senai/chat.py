"""Interactive Senai conversation using the shared request pipeline and durable history."""
import sqlite3
from pathlib import Path

from .chat_store import ChatStore
from .workspace import prepare_workspace

HELP = "/help /history [all] /sessions /resume LOCAL_SESSION_ID /new /exit"


def show_history(store, installation, stdout, identifier=None):
    turns = store.history(installation, identifier)
    if not turns:
        print("No saved turns.", file=stdout)
    for turn in turns:
        print(f"[{turn['session']} / {turn['status']}] You: {turn['request']}", file=stdout)
        print("Senai: " + turn['response'], file=stdout)
    if len(turns) == 200:
        print("Showing latest 200 turns; the complete transcript remains in the database.", file=stdout)


def show_sessions(store, installation, stdout):
    sessions = store.sessions(installation)
    if not sessions:
        print("No saved sessions.", file=stdout)
    for session in sessions:
        print(session['id'] + "  native=" + (session['native_id'] or "not started"), file=stdout)


def chat_main(argv, stdout, stderr, stdin):
    from .cli import build_parser, execute_request
    parser = build_parser()
    parser.prog = "senai chat"
    parser.description = "Persistent Senai chat with memory, selected skills and saved native sessions."
    parser.epilog = HELP
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--new', action='store_true', help='Start a fresh local chat; keep old history.')
    group.add_argument('--session', metavar='ID', help='Resume a saved local chat ID from --sessions.')
    group.add_argument('--history', action='store_true', help='Show saved history across local sessions and exit.')
    group.add_argument('--sessions', action='store_true', help='List local/native session IDs and exit.')
    args = parser.parse_args(argv)
    try:
        if args.json or args.ephemeral or args.last or args.resume or args.version:
            raise ValueError("Persistent chat uses text and managed sessions. Use --session LOCAL_ID, /new or /history; native --resume/--last/--ephemeral/--json/--version are not chat modes.")
        if args.worktree or args.add_dir:
            raise ValueError("Chat cannot relocate or expand the outputs workspace.")
        workspace = prepare_workspace(args.project)
        args.project = str(workspace.parent)
        installation = str(Path(args.installation).expanduser().resolve()) if args.installation else ''
        if installation and not Path(installation).is_dir():
            raise ValueError("Memory installation must be an existing directory. Run senai setup.")
        args.installation = installation
        store = ChatStore(workspace)
        if args.history:
            show_history(store, installation, stdout)
            return 0
        if args.sessions:
            show_sessions(store, installation, stdout)
            return 0
        with store.exclusive():
            session = store.select(installation, identifier=args.session, fresh=args.new)
            print("Senai chat " + session['id'] + "; " + HELP, file=stdout)
            print("History: " + str(store.path), file=stdout)
            if not installation:
                print("Memory is not configured; run senai setup to enable installation profiles.", file=stderr)
            pending = args.request
            while True:
                if pending is not None:
                    text, pending = pending, None
                else:
                    if stdin.isatty():
                        print("you> ", file=stdout, end='', flush=True)
                    line = stdin.readline()
                    if not line:
                        return 0
                    text = line.strip()
                if not text:
                    continue
                if text in ('/exit', '/quit'):
                    return 0
                if text == '/help':
                    print(HELP, file=stdout)
                    continue
                if text in ('/history', '/history all'):
                    show_history(store, installation, stdout, session['id'] if text == '/history' else None)
                    continue
                if text == '/sessions':
                    show_sessions(store, installation, stdout)
                    continue
                if text == '/new':
                    session = store.select(installation, fresh=True)
                    print("Fresh chat: " + session['id'] + "; earlier history retained.", file=stdout)
                    continue
                if text.startswith('/resume '):
                    session = store.select(installation, identifier=text.split(' ', 1)[1].strip())
                    print("Resumed chat: " + session['id'], file=stdout)
                    continue
                if text.startswith('/'):
                    print("Unknown chat command. " + HELP, file=stderr)
                    continue
                session = store.session(session['id'], installation)
                args.resume = session['native_id']
                turn = store.begin(session['id'], text)
                observed = []
                def bind(native_id):
                    store.bind(session['id'], installation, native_id)
                    observed.append(native_id)
                try:
                    response = execute_request(args, text, stdout=stdout, stderr=stderr,
                                               stdin=stdin, session_callback=bind)
                    if not observed:
                        raise RuntimeError("No native session ID observed; effects unknown.")
                    # Commit before displaying: reopening does not execute this turn again.
                    store.finish(turn, response)
                except BaseException:
                    store.finish(turn, "Execution interrupted or failed; effects unknown. Inspect before new work.", status='unknown')
                    raise
                print(response, file=stdout)
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as error:
        print("senai chat: " + str(error), file=stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("senai chat: Interrupted; saved history retained.", file=stderr)
        return 130
