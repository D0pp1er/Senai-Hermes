"""Single-use local pairing codes; only their hashes are stored."""

import hashlib
import secrets
import time


class PairingManager:
    def __init__(self, store, *, clock=time.time):
        self.store, self.clock = store, clock

    def issue(self, *, ttl=600):
        if not 1 <= ttl <= 3600:
            raise ValueError('Pairing expiry must be between 1 and 3600 seconds.')
        code = secrets.token_urlsafe(18)
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self.store.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            database.execute('UPDATE pairing_codes SET used=1 WHERE used=0')
            database.execute('INSERT INTO pairing_codes(digest,expires,used) VALUES (?,?,0)', (digest, self.clock() + ttl))
        return code

    def redeem(self, code, user_id, chat_id):
        if not isinstance(code, str) or type(user_id) is not int or user_id <= 0 or chat_id != user_id:
            return False
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self.store.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            row = database.execute('SELECT expires,used FROM pairing_codes WHERE digest=?', (digest,)).fetchone()
            if row is None or row['used'] or row['expires'] <= self.clock():
                return False
            database.execute('UPDATE pairing_codes SET used=1 WHERE digest=?', (digest,))
            database.execute('INSERT INTO paired_users(user_id,active,updated) VALUES (?,1,?) ON CONFLICT(user_id) DO UPDATE SET active=1,updated=excluded.updated', (user_id, self.clock()))
        return True
