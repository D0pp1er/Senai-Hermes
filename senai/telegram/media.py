"""Workspace-only media snapshots and an independent durable upload cursor."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3

from .api import TelegramError
from .speech import is_mp3, MAX_AUDIO_BYTES

__all__ = ['MediaOutbox']

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGES = 4


class MediaOutbox:
    def __init__(self, workspace, state_dir):
        workspace, state_dir = Path(workspace), Path(state_dir)
        if workspace.is_symlink() or state_dir.is_symlink():
            raise ValueError('Media workspace/state cannot be symlinked.')
        self.workspace, self.state = workspace.resolve(), state_dir.resolve()
        if not self.state.is_relative_to(self.workspace) or self.state == self.workspace:
            raise ValueError('Media state must be inside outputs/.')
        self.state.mkdir(parents=True, exist_ok=True)
        self.path = self.state / 'media.sqlite3'
        if self.path.is_symlink():
            raise ValueError('Media database cannot be symlinked.')
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS uploads (job_id INTEGER PRIMARY KEY, items TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS voice_requests (job_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, prompt_hash TEXT NOT NULL, mode TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS voice_delivery (job_id INTEGER PRIMARY KEY, outcome TEXT NOT NULL)')
        self.path.chmod(0o600)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _existing(self, job_id):
        with self._db() as db:
            return db.execute('SELECT items,sent FROM uploads WHERE job_id=?', (job_id,)).fetchone()

    def record_voice_request(self, job_id, job, *, reuse=False):
        # Record before enqueue so the worker cannot race ahead of its reply mode.
        # Binding to sender, target and exact prompt prevents stale/orphan metadata reuse.
        digest = hashlib.sha256(job['prompt'].encode('utf-8')).hexdigest()
        with self._db() as db:
            db.execute('INSERT OR IGNORE INTO voice_requests VALUES (?,?,?,?,?)',
                       (job_id, job['user_id'], job['chat_id'], digest, 'reuse' if reuse else 'question'))

    def voice_mode(self, job):
        with self._db() as db:
            row = db.execute('SELECT user_id,chat_id,prompt_hash,mode FROM voice_requests WHERE job_id=?',
                             (job['id'],)).fetchone()
        if row is None:
            return None
        digest = hashlib.sha256(job['prompt'].encode('utf-8')).hexdigest()
        if (job.get('user_id'), job.get('chat_id'), digest) != row[:3]:
            return None
        return row[3]

    def _image(self, relative):
        if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
            raise ValueError('Image must be a relative workspace filename.')
        path = Path(relative)
        if path.is_absolute() or any(part == '..' or part.startswith('.') for part in path.parts):
            raise ValueError('Image must be a visible workspace file.')
        source = self.workspace / path
        for parent in (source, *source.parents):
            if parent == self.workspace:
                break
            if parent.is_symlink():
                raise ValueError('Symlinked media is not supported.')
        resolved = source.resolve()
        if not resolved.is_relative_to(self.workspace) or resolved.is_relative_to(self.state):
            raise ValueError('Private state and external files cannot be attached.')
        if resolved.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            raise ValueError('Use PNG or JPEG images.')
        with resolved.open('rb') as stream:
            content = stream.read(MAX_IMAGE_BYTES + 1)
        if not content or len(content) > MAX_IMAGE_BYTES:
            raise ValueError('Image exceeds the upload limit.')
        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            suffix = '.png'
        elif content.startswith(b'\xff\xd8\xff'):
            suffix = '.jpg'
        else:
            raise ValueError('File is not a PNG or JPEG image.')
        return content, suffix

    def _state_path(self, relative):
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid media snapshot path.')
        path = self.state / relative
        for parent in (path, *path.parents):
            if parent == self.state:
                break
            if parent.is_symlink():
                raise ValueError('Media snapshot directories cannot be symlinked.')
        if not path.resolve().is_relative_to(self.state):
            raise ValueError('Media snapshot must stay inside its state directory.')
        return path

    def _save(self, job_id, assets):
        directory = self._state_path(Path('media') / str(job_id))
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        items = []
        for index, (kind, content, suffix) in enumerate(assets):
            target = directory / (str(index) + suffix)
            if target.is_symlink():
                raise ValueError('Media snapshot cannot be symlinked.')
            target.write_bytes(content)
            target.chmod(0o600)
            items.append({'kind': kind, 'path': str(target.relative_to(self.state)),
                          'sha256': hashlib.sha256(content).hexdigest()})
        with self._db() as db:
            db.execute('INSERT OR IGNORE INTO uploads(job_id,items) VALUES (?,?)', (job_id, json.dumps(items)))

    def prepare(self, job_id, manifest):
        if self._existing(job_id):
            return
        manifest = Path(manifest)
        if manifest.is_symlink():
            raise ValueError('Attachment manifest cannot be symlinked.')
        if not manifest.exists():
            self._save(job_id, [])
            return
        with manifest.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('Attachment manifest is too large.')
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {'images'} or not isinstance(data['images'], list):
            raise ValueError('Expected an images array.')
        if len(data['images']) > MAX_IMAGES:
            raise ValueError('Use at most four images per reply.')
        if not all(isinstance(value, str) for value in data['images']):
            raise ValueError('Image filenames must be strings.')
        assets = [('photo', *self._image(value)) for value in dict.fromkeys(data['images'])]
        self._save(job_id, assets)

    def add_voice(self, job_id, content):
        if not is_mp3(content) or len(content) > MAX_AUDIO_BYTES:
            raise ValueError('Unsupported voice audio.')
        record = self._existing(job_id)
        if record is None:
            self._save(job_id, [])
            record = self._existing(job_id)
        items, sent = json.loads(record[0]), record[1]
        if any(item['kind'] == 'voice' for item in items):
            return
        if sent:
            raise ValueError('Cannot add voice after delivery has started.')
        path = self._state_path(Path('media') / str(job_id) / 'voice.mp3')
        if path.is_symlink():
            raise ValueError('Voice snapshot cannot be symlinked.')
        path.write_bytes(content)
        path.chmod(0o600)
        items.append({'kind': 'voice', 'path': str(path.relative_to(self.state)),
                      'sha256': hashlib.sha256(content).hexdigest()})
        with self._db() as db:
            db.execute('UPDATE uploads SET items=? WHERE job_id=? AND sent=0', (json.dumps(items), job_id))

    def has_voice(self, job_id):
        record = self._existing(job_id)
        return record is not None and any(item['kind'] == 'voice' for item in json.loads(record[0]))

    def _read_snapshot(self, item):
        path = self._state_path(item['path'])
        with path.open('rb') as stream:
            content = stream.read(MAX_IMAGE_BYTES + 1)
        if hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ValueError('Media snapshot changed.')
        return path

    def deliver_voice(self, job, api, *, authorized):
        """Persist audio success or text fallback so retries never switch formats."""
        if not authorized():
            return 'revoked'
        with self._db() as db:
            row = db.execute('SELECT outcome FROM voice_delivery WHERE job_id=?', (job['id'],)).fetchone()
        if row is not None:
            return row[0]
        record = self._existing(job['id'])
        voice = next((item for item in json.loads(record[0]) if item['kind'] == 'voice'), None) if record else None
        outcome = 'fallback'
        if voice is not None:
            try:
                path = self._read_snapshot(voice)
                api.send_voice(job['chat_id'], path)
                outcome = 'audio'
            except TelegramError as error:
                if error.status in (401, 403, 409):
                    raise
            except (OSError, ValueError):
                pass
        with self._db() as db:
            db.execute('INSERT OR IGNORE INTO voice_delivery VALUES (?,?)', (job['id'], outcome))
        return outcome

    def deliver(self, job, api, *, authorized, skip_voice=False):
        record = self._existing(job['id'])
        if record is None:
            return
        items, sent = json.loads(record[0]), record[1]
        for index, item in enumerate(items[sent:], sent):
            if not authorized():
                return
            if not (skip_voice and item['kind'] == 'voice'):
                try:
                    path = self._read_snapshot(item)
                except (OSError, ValueError):
                    api.send_message(job['chat_id'], 'An attachment is no longer available. Please request it again.')
                else:
                    try:
                        if item['kind'] == 'voice':
                            api.send_voice(job['chat_id'], path)
                        else:
                            api.send_photo(job['chat_id'], path)
                    except TelegramError as error:
                        if error.status != 400 and error.status != 413:
                            raise
                        message = ('Telegram could not play the voice reply. Please request the text with /result.'
                                   if item['kind'] == 'voice' else 'Telegram could not display an image. Please request a smaller PNG or JPEG.')
                        api.send_message(job['chat_id'], message)
            with self._db() as db:
                db.execute('UPDATE uploads SET sent=? WHERE job_id=?', (index + 1, job['id']))
