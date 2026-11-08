"""Run or configure the WSL Telegram bot adapter."""

import argparse
from pathlib import Path
import secrets

from .api import BotAPI, TelegramError
from .config import load_credentials
from .router import Router
from .runner import CommandRunner
from .service import BotService, instance_lock
from .store import JobStore
from ..workspace import prepare_workspace


def discover_user(api, username, stdout):
    phrase = 'senai-setup-' + secrets.token_hex(8)
    print(f'Send this exact private message to @{username}: {phrase}', file=stdout, flush=True)
    offset = None
    while True:
        for update in api.get_updates(offset, timeout=10):
            if not isinstance(update, dict) or type(update.get('update_id')) is not int:
                continue
            offset = update['update_id'] + 1
            message = update.get('message', {})
            sender, chat = message.get('from', {}), message.get('chat', {})
            if message.get('text') == phrase and chat.get('type') == 'private' and type(sender.get('id')) is int and sender['id'] == chat.get('id') and not sender.get('is_bot'):
                print(f'TELEGRAM_ALLOWED_USER_IDS={sender["id"]}', file=stdout, flush=True)
                print('Setup only: no code was executed and no bot reply was sent.', file=stdout)
                return 0


def telegram_main(argv, stdout, stderr):
    parser = argparse.ArgumentParser(prog='senai telegram', description='Control local senai through an authorized private Telegram bot.')
    parser.add_argument('--project', default='.', help='Parent project; code and bot state stay inside outputs/.')
    parser.add_argument('--env-file', help='Optional local token/user-ID assignments; never a shell script.')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--setup', action='store_true', help='Discover your numeric user ID without executing requests.')
    modes.add_argument('--check', action='store_true', help='Check bot identity and webhook compatibility, without polling or execution.')
    parser.add_argument('--skip-git-repo-check', action='store_true', help='Allow the selected non-Git project.')
    parser.add_argument('-m', '--model', help='Fixed Codex model for requests.')
    parser.add_argument('-p', '--profile', help='Fixed Codex configuration profile.')
    parser.add_argument('--search', action='store_true', help='Enable search for every bot request.')
    parser.add_argument('--skill', action='append', default=[], help='Installed skill to use for each request; repeatable.')
    parser.add_argument('--max-pending', type=int, default=4, help='Maximum queued plus running requests (1-100, default 4).')
    parser.add_argument('--poll-timeout', type=int, default=10, help='Long-poll timeout in seconds (1-30).')
    args = parser.parse_args(argv)
    api = None
    try:
        if not 1 <= args.max_pending <= 100 or not 1 <= args.poll_timeout <= 30:
            raise ValueError('Use --max-pending between 1 and 100 and --poll-timeout between 1 and 30.')
        token, users = load_credentials(env_file=args.env_file, require_users=not (args.setup or args.check))
        api = BotAPI(token)
        identity = api.get_me()
        if not isinstance(identity, dict) or identity.get('is_bot') is not True or type(identity.get('id')) is not int or identity['id'] <= 0 or not isinstance(identity.get('username'), str):
            raise ValueError('Telegram returned an invalid bot identity.')
        info = api.get_webhook_info()
        if not isinstance(info, dict) or info.get('url'):
            raise ValueError('This bot has an active webhook. Use a dedicated bot or remove that webhook explicitly before polling; senai will not delete it automatically.')
        if args.check:
            print(f'Connected to @{identity["username"]}; webhook is off. Execution still requires an allowed-user list.', file=stdout)
            return 0
        if args.setup:
            return discover_user(api, identity['username'], stdout)
        workspace = prepare_workspace(args.project)
        state = workspace / '.senai-telegram' / str(identity['id'])
        if not state.resolve().is_relative_to(workspace.resolve()):
            raise ValueError('Telegram state must stay inside outputs/.')
        state.mkdir(parents=True, exist_ok=True)
        state.chmod(0o700)
        with instance_lock(state / 'bot.lock'):
            store = JobStore(state / 'state.sqlite3')
            router = Router(store, users, identity['username'], max_pending=args.max_pending)
            runner = CommandRunner(args.project, state, store=store, skip_git_repo_check=args.skip_git_repo_check, model=args.model, profile=args.profile, search=args.search, skills=tuple(args.skill))
            runner.recover_session()
            store.recover_interrupted()
            service = BotService(api, store, router, runner, poll_timeout=args.poll_timeout)
            service.skip_pending()
            print(f'Senai Telegram is ready as @{identity["username"]}. Project: {Path(args.project).expanduser().resolve()}. One shared persistent Codex session; messages from before startup are ignored.', file=stdout, flush=True)
            return service.run_forever(stdout, stderr)
    except (ValueError, RuntimeError, OSError) as error:
        message = api.redact(str(error)) if api else str(error)
        print(f'senai telegram: {message}', file=stderr)
        return 2
    except KeyboardInterrupt:
        return 130
