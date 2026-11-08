"""Read bot credentials without executing shell configuration."""

import os
import hashlib
import tempfile
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


def default_env_file(project):
    identity = hashlib.sha256(str(Path(project).expanduser().resolve()).encode()).hexdigest()[:20]
    base = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))).expanduser()
    return base / 'senai' / 'telegram' / f'{identity}.env'


def write_token_file(path, token):
    token, _ = load_credentials({'TELEGRAM_BOT_TOKEN': token}, require_users=False)
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError('Refusing a symlinked Telegram credential file.')
    existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not existed:
        path.parent.chmod(0o700)
    descriptor, temporary = tempfile.mkstemp(prefix='.telegram-', dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write('TELEGRAM_BOT_TOKEN=' + token + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
