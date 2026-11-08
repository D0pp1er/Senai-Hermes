"""Interactive, operator-independent setup; secrets never appear in output."""

from dataclasses import dataclass, field
import getpass
from pathlib import Path

from .api import BotAPI
from .config import default_env_file, load_credentials, write_token_file
from .connection import identify_bot, state_directory
from .pairing import PairingManager
from .service import instance_lock
from .store import JobStore


@dataclass(frozen=True)
class Configuration:
    token: str = field(repr=False)
    env_file: Path
    username: str


def configure_project(project, *, env_file=None, stdout, prompt=None, api_factory=None, environ=None):
    project = Path(project).expanduser().resolve()
    if not project.is_dir():
        raise ValueError('Project must be an existing directory.')
    path = Path(env_file).expanduser() if env_file else default_env_file(project)
    if path.resolve().is_relative_to(project):
        raise ValueError('Keep the bot credential file outside the controlled project and its outputs/.')
    existing = None
    try:
        existing, _ = load_credentials(environ, env_file=path if path.is_file() else None, require_users=False)
    except ValueError:
        pass
    prompt = prompt or getpass.getpass
    entered = prompt('Telegram bot token (hidden; Enter keeps saved token): ').strip()
    token, _ = load_credentials({'TELEGRAM_BOT_TOKEN': entered or existing or ''}, require_users=False)
    api = (api_factory or BotAPI)(token)
    identity = identify_bot(api)
    state = state_directory(project, identity['id'])
    with instance_lock(state / 'bot.lock'):
        store = JobStore(state / 'state.sqlite3')
        pairing = PairingManager(store)
        pending = api.get_updates(-1, timeout=0)
        identifiers = [item['update_id'] for item in pending if isinstance(item, dict) and type(item.get('update_id')) is int]
        offset = max(identifiers) + 1 if identifiers else None
        code = pairing.issue()
        print(f'Bot: @{identity["username"]}. All paired users share one Codex conversation.', file=stdout, flush=True)
        print(f'Send this private message to the bot within 10 minutes: /pair {code}', file=stdout, flush=True)
        while True:
            for update in api.get_updates(offset, timeout=10):
                if not isinstance(update, dict) or type(update.get('update_id')) is not int:
                    continue
                offset = update['update_id'] + 1
                message = update.get('message')
                if not isinstance(message, dict):
                    continue
                sender, chat = message.get('from'), message.get('chat')
                if not isinstance(sender, dict) or not isinstance(chat, dict):
                    continue
                expected = (f'/pair {code}', f'/pair@{identity["username"]} {code}')
                if message.get('text') not in expected or chat.get('type') != 'private' or sender.get('is_bot'):
                    continue
                if pairing.redeem(code, sender.get('id'), chat.get('id')):
                    store.consume(update['update_id'])
                    write_token_file(path, token)
                    print(f'Paired Telegram account {sender["id"]}. Saved private configuration: {path}', file=stdout, flush=True)
                    print('No manual export or numeric user-ID lookup is needed.', file=stdout)
                    return Configuration(token, path, identity['username'])
                code = pairing.issue()
                print(f'Code expired; send this new private message: /pair {code}', file=stdout, flush=True)
