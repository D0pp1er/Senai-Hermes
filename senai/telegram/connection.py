"""Shared identity validation and project-local state preparation."""

from ..workspace import prepare_workspace


def identify_bot(api):
    identity = api.get_me()
    if not isinstance(identity, dict) or identity.get('is_bot') is not True or type(identity.get('id')) is not int or identity['id'] <= 0 or not isinstance(identity.get('username'), str) or not identity['username']:
        raise ValueError('Telegram returned an invalid bot identity.')
    info = api.get_webhook_info()
    if not isinstance(info, dict) or info.get('url'):
        raise ValueError('This bot has an active webhook. Use a dedicated bot or remove that webhook explicitly before polling; senai will not delete it automatically.')
    return identity


def state_directory(project, bot_id):
    workspace = prepare_workspace(project)
    state = workspace / '.senai-telegram' / str(bot_id)
    if not state.resolve().is_relative_to(workspace.resolve()):
        raise ValueError('Telegram state must stay inside outputs/.')
    state.mkdir(parents=True, exist_ok=True)
    state.chmod(0o700)
    return state
