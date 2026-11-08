"""Optional project-scoped voice credentials, kept outside the controlled project."""

from dataclasses import dataclass, field
import getpass
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import warnings

from .speech import OpenAISpeech

__all__ = ['VoiceConfigError', 'default_voice_file', 'write_voice_key',
           'read_voice_key', 'remove_voice_key', 'resolve_voice_key',
           'configure_voice', 'offer_voice_setup', 'speech_from_configuration', 'manage_voice']


class VoiceConfigError(ValueError):
    """Messages contain no credential or raw underlying exception text."""


@dataclass(frozen=True)
class VoiceKey:
    key: str = field(repr=False)
    source: str


def _values(environ):
    return os.environ if environ is None else environ


def default_voice_file(project, *, environ=None):
    project = Path(project).expanduser().resolve()
    identity = hashlib.sha256(str(project).encode()).hexdigest()[:20]
    base = Path(_values(environ).get('XDG_CONFIG_HOME', str(Path.home() / '.config'))).expanduser()
    return base / 'senai' / 'voice' / (identity + '.json')


def _path(project, environ):
    project = Path(project).expanduser().resolve()
    if not project.is_dir():
        raise VoiceConfigError('Project must be an existing directory.')
    path = default_voice_file(project, environ=environ).absolute()
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise VoiceConfigError('Voice configuration paths must not contain symlinks.')
        if parent.is_dir() and ((parent / '.git').exists() or (parent / '.git').is_symlink()):
            raise VoiceConfigError('Voice credentials must remain outside Git repositories.')
    if path.resolve().is_relative_to(project):
        raise VoiceConfigError('Voice credentials must remain outside the controlled project.')
    return path


def _key(value):
    if (not isinstance(value, str) or not value or len(value) > 4096 or
            not value.isascii() or any(ord(char) < 33 or ord(char) > 126 for char in value)):
        raise VoiceConfigError('Enter a valid API key through hidden local input.')
    return value


def _owned_regular(info):
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise VoiceConfigError('Voice configuration must be a private regular file owned by this user.')


def write_voice_key(project, key, *, environ=None):
    key = _key(key)
    path = _path(project, environ)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.parent.stat().st_uid != os.getuid():
            raise VoiceConfigError('Voice configuration directory must be owned by this user.')
        path.parent.chmod(0o700)
        if path.exists():
            _owned_regular(path.lstat())
        descriptor, temporary = tempfile.mkstemp(prefix='.voice-', dir=path.parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump({'version': 1, 'api_key': key}, stream)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        raise VoiceConfigError('Could not save protected voice configuration.') from None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def read_voice_key(project, *, environ=None):
    path = _path(project, environ)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError:
        raise VoiceConfigError('Could not read protected voice configuration.') from None
    try:
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            _owned_regular(info)
            if stat.S_IMODE(info.st_mode) & 0o077 or not info.st_mode & stat.S_IRUSR:
                raise VoiceConfigError('Voice configuration permissions must be private (chmod 600).')
            if path.parent.stat().st_uid != os.getuid() or stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
                raise VoiceConfigError('Voice configuration directory must be private (chmod 700).')
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise VoiceConfigError('Voice configuration is invalid; configure it again locally.')
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {'version', 'api_key'} or type(data['version']) is not int or data['version'] != 1:
            raise VoiceConfigError('Voice configuration has an unsupported format.')
        return _key(data['api_key'])
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise VoiceConfigError('Voice configuration is invalid; configure it again locally.') from None


def remove_voice_key(project, *, environ=None):
    path = _path(project, environ)
    try:
        _owned_regular(path.lstat())
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        raise VoiceConfigError('Could not remove saved voice configuration.') from None


def resolve_voice_key(project, *, environ=None):
    values = _values(environ)
    dedicated = values.get('SENAI_TTS_API_KEY', '').strip()
    if dedicated:
        return VoiceKey(_key(dedicated), 'SENAI_TTS_API_KEY environment')
    saved = read_voice_key(project, environ=environ)
    if saved:
        return VoiceKey(saved, 'protected saved file')
    generic = values.get('OPENAI_API_KEY', '').strip()
    return VoiceKey(_key(generic), 'OPENAI_API_KEY environment') if generic else None


def speech_from_configuration(project, *, environ=None):
    selected = resolve_voice_key(project, environ=environ)
    if selected is None:
        return None
    values = _values(environ)
    return OpenAISpeech(selected.key, model=values.get('SENAI_TTS_MODEL', 'gpt-4o-mini-tts'),
                        voice=values.get('SENAI_TTS_VOICE', 'coral'))


def _hidden_key(prompt=None):
    try:
        with warnings.catch_warnings():
            # Never allow getpass's non-TTY fallback to echo a secret.
            warnings.simplefilter('error', getpass.GetPassWarning)
            return (prompt or getpass.getpass)('OpenAI voice API key (hidden; Enter keeps saved key or skips): ').strip()
    except (getpass.GetPassWarning, EOFError, OSError, ValueError):
        raise VoiceConfigError('Hidden local input requires a secure terminal; no key was saved.') from None


def _restart_notice(stdout):
    print('If a bot is running, changes apply after a graceful restart: stop the existing bot with Ctrl+C, wait for it to exit, then start it once using the same project/config. Do not start a duplicate bot.', file=stdout)
    print('Environment keys remain supported and may still enable voice after saved-key removal.', file=stdout)


def configure_voice(project, *, stdout, prompt=None, environ=None):
    _path(project, environ)  # Fail before asking for a secret if the location is unsafe.
    entered = _hidden_key(prompt)
    if not entered:
        print('Saved voice configuration kept; voice setup skipped.' if read_voice_key(project, environ=environ) else 'Voice setup skipped. Telegram works without voice.', file=stdout)
        return False
    write_voice_key(project, entered, environ=environ)
    print('Voice key saved privately, separate from Telegram credentials. /voice sends text and matching audio. OpenAI speech API usage is billed separately.', file=stdout)
    _restart_notice(stdout)
    return True


def offer_voice_setup(project, *, stdout, choice=None, prompt=None, environ=None):
    print('Optional voice replies: /voice sends text and matching audio using the OpenAI speech API (separate API billing). Telegram works without it.', file=stdout)
    try:
        answer = (choice or input)('Configure optional voice? [Configure/Skip; Enter=Skip]: ').strip().lower()
        if answer not in ('y', 'yes', 'configure'):
            print('Voice setup skipped; existing settings are unchanged. Configure later with senai telegram --voice-configure --project YOUR_PROJECT.', file=stdout)
            return False
        return configure_voice(project, stdout=stdout, prompt=prompt, environ=environ)
    except (EOFError, KeyboardInterrupt, OSError, VoiceConfigError):
        print('Voice setup skipped; Telegram remains configured. Use --voice-configure later from a secure local terminal.', file=stdout)
        return False


def manage_voice(project, action, *, stdout, stderr, prompt=None, environ=None):
    """Local-only management: never contacts Telegram, speech APIs or a bot process."""
    try:
        if action == 'configure':
            configure_voice(project, stdout=stdout, prompt=prompt, environ=environ)
        elif action == 'remove':
            removed = remove_voice_key(project, environ=environ)
            print('Saved voice key removed.' if removed else 'No saved voice key to remove.', file=stdout)
            _restart_notice(stdout)
        elif action == 'check':
            selected = resolve_voice_key(project, environ=environ)
            if selected is None:
                print('Voice is not configured. Telegram works without voice.', file=stdout)
                return 1
            print(f'Voice configured via {selected.source}. Local check only; API access and billing have not been verified. /voice sends text and matching audio.', file=stdout)
        else:
            raise VoiceConfigError('Unsupported voice management action.')
        return 0
    except KeyboardInterrupt:
        print('Voice configuration cancelled. No bot was started or restarted.', file=stderr)
        return 130
    except (VoiceConfigError, OSError, EOFError):
        print('Voice configuration could not be completed. Check the protected local file/permissions or retry hidden input in a secure terminal. Telegram configuration is unchanged.', file=stderr)
        return 2
