"""Compatibility adapter over Telegram's existing router, queue and session policy."""

from pathlib import Path

from .contract import IncomingRequest
from ..telegram.formatting import split_message


def parse_private_update(update):
    """Validate shape only; pairing and revocation remain router decisions."""
    if not isinstance(update, dict):
        return None
    identifier = update.get('update_id')
    if type(identifier) is not int or identifier < 0:
        return None
    message = update.get('message')
    if not isinstance(message, dict):
        return None
    sender, chat = message.get('from'), message.get('chat')
    if not isinstance(sender, dict) or not isinstance(chat, dict):
        return None
    user, target, text = sender.get('id'), chat.get('id'), message.get('text')
    if (type(user) is not int or user <= 0 or sender.get('is_bot') is True
            or chat.get('type') != 'private' or type(target) is not int
            or target != user or not isinstance(text, str)):
        return None
    return identifier, user, target, text


class TelegramAdapter:
    """Account is the verified bot ID; project is the configured parent project.

    One existing store/router belongs to exactly one bot/project. Normalization
    never queues or authorizes. handle delegates all commands, including pairing,
    to the legacy router. It does not introduce a second queue or native session.
    """

    def __init__(self, router, api, *, project, account):
        if not isinstance(account, str) or not account.strip():
            raise ValueError('An explicit Telegram account identity is required.')
        self.router, self.api = router, api
        self.project = str(Path(project).expanduser().resolve())
        self.account = account.strip()

    def normalize(self, event):
        parsed = parse_private_update(event)
        if parsed is None:
            return None
        identifier, user, target, text = parsed
        return IncomingRequest('telegram', self.account, self.project, str(identifier),
                               str(user), str(target), text, 'telegram-shared')

    def is_authorized(self, user_id):
        # Also accept the existing worker's integer IDs; reject bool/float coercion.
        if type(user_id) is int:
            return user_id > 0 and self.router.is_authorized(user_id)
        if not isinstance(user_id, str) or not user_id.isascii() or not user_id.isdecimal():
            return False
        return int(user_id) > 0 and self.router.is_authorized(int(user_id))

    def handle(self, event):
        return self.router.handle(event)

    def delivery_parts(self, text):
        return split_message(self.api.redact(text))

    def send_text(self, target, text):
        for part in self.delivery_parts(text):
            self.api.send_message(int(target), part)
