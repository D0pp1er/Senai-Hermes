"""Workspace-only media snapshots and an independent durable upload cursor."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3

from .api import TelegramError

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

    def _save(self, job_id, assets):
        directory = self.state / 'media' / str(job_id)
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

    def deliver(self, job, api, *, authorized):
        record = self._existing(job['id'])
        if record is None:
            return
        items, sent = json.loads(record[0]), record[1]
        for index, item in enumerate(items[sent:], sent):
            if not authorized():
                return
            path = self.state / item['path']
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(self.state):
                    raise ValueError('Invalid media snapshot.')
                with path.open('rb') as stream:
                    content = stream.read(MAX_IMAGE_BYTES + 1)
                if hashlib.sha256(content).hexdigest() != item['sha256']:
                    raise ValueError('Media snapshot changed.')
            except (OSError, ValueError):
                api.send_message(job['chat_id'], 'An attachment is no longer available. Please request it again.')
            else:
                try:
                    api.send_photo(job['chat_id'], path)
                except TelegramError as error:
                    if error.status != 400 and error.status != 413:
                        raise
                    api.send_message(job['chat_id'], 'Telegram could not display an image. Please request a smaller PNG or JPEG.')
            with self._db() as db:
                db.execute('UPDATE uploads SET sent=? WHERE job_id=?', (index + 1, job['id']))
