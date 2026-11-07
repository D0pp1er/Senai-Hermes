"""Read bot credentials without executing shell configuration."""

import os
import re
from pathlib import Path

KEYS = {'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USER_IDS'}


def load_credentials(environ=None, *, env_file=None, require_users=True):
    values = {}
    if env_file:
        for line in Path(env_file).expanduser().read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, separator, value = line.partition('=')
            if not separator or key.strip() not in KEYS:
                raise ValueError('Telegram env file must contain only TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_IDS assignments.')
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            values[key.strip()] = value
    values.update(os.environ if environ is None else environ)
    token = values.get('TELEGRAM_BOT_TOKEN', '').strip()
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token):
        raise ValueError('Set a valid TELEGRAM_BOT_TOKEN locally; do not paste it into chat.')
    entries = values.get('TELEGRAM_ALLOWED_USER_IDS', '').strip()
    try:
        users = frozenset(int(value.strip()) for value in entries.split(',') if value.strip())
    except ValueError:
        raise ValueError('TELEGRAM_ALLOWED_USER_IDS must be comma-separated positive numeric user IDs.') from None
    if any(user <= 0 for user in users) or (require_users and not users):
        raise ValueError('Set TELEGRAM_ALLOWED_USER_IDS to your positive numeric Telegram user ID. Use --setup to discover it.')
    return token, users
