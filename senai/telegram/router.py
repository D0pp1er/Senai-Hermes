"""Authorize private updates before routing text into the durable request queue."""

from .pairing import PairingManager
from ..integrations.telegram import parse_private_update

HELP = (
    'Send a code request as text, or /run your request.\n'
    '/voice QUESTION - get a text and AI-generated voice reply; /voice reads your latest answer\n'
    '/status - latest requests and their states\n'
    '/result - resend your latest completed result\n'
    '/session - show the shared Codex session\n'
    '/pair CODE - pair using a code shown locally\n'
    '/help - show this message\n'
    'Paired users share one persistent Codex conversation; generated files stay in the configured outputs/. '
    'Only paired private users or configured allowed users can execute requests.'
)


def result_text(job):
    if job['status'] == 'succeeded':
        return job['result']
    return f'Request #{job["id"]}: {job["status"]}\n\n{job["result"]}'


class Router:
    def __init__(self, store, allowed_users, username, *, max_pending=4, acknowledge=None, voice_enabled=False, media=None):
        self.store = store
        self.allowed_users = allowed_users
        self.username = username.lower()
        self.max_pending = max_pending
        self.acknowledge = acknowledge
        self.voice_enabled = voice_enabled
        self.media = media

    def is_authorized(self, user_id):
        status = self.store.user_status(user_id)
        return status if status is not None else user_id in self.allowed_users

    def handle(self, update):
        identifier = update.get('update_id') if isinstance(update, dict) else None
        if type(identifier) is not int or identifier < 0:
            return []
        parsed = parse_private_update(update)
        if parsed is None:
            self.store.consume(identifier)
            return []
        _, user_id, chat_id, text = parsed
        sender, chat = {'id': user_id}, {'id': chat_id}
        text = text.strip()
        command, argument = '', ''
        if text.startswith('/'):
            parts = text.split(maxsplit=1)
            name = parts[0]
            command, separator, mention = name.partition('@')
            if separator and mention.lower() != self.username:
                self.store.consume(identifier)
                return []
            argument = parts[1].strip() if len(parts) > 1 else ''
        if command == '/pair':
            if self.store.consume(identifier) == 'duplicate':
                return []
            paired = PairingManager(self.store).redeem(argument, sender['id'], chat['id'])
            response = 'Paired successfully. You share the existing Codex conversation; send /help to begin.' if paired else 'Pairing failed. Ask the local operator for a new, unexpired code.'
            return [(chat['id'], response)]
        if not self.is_authorized(sender['id']):
            self.store.consume(identifier)
            return []
        prompt = argument if command in ('/run', '/voice') else text
        voice_error, reuse_voice = None, False
        if command == '/voice':
            if not self.voice_enabled or self.media is None:
                voice_error = 'Voice replies are not configured yet. You can still ask in text.'
            elif not argument:
                previous = self.store.latest_completed(chat['id'])
                if previous is None or previous['status'] != 'succeeded':
                    voice_error = 'No answer to read yet. Use /voice your question.'
                elif len(previous['result']) > 4000:
                    voice_error = 'That answer is too long for a voice note. Use /voice and ask for a shorter summary.'
                else:
                    prompt, reuse_voice = previous['result'], True
        is_request = (not command or command in ('/run', '/voice')) and bool(prompt) and len(prompt) <= 8000 and voice_error is None
        job = {'chat_id': chat['id'], 'user_id': sender['id'], 'prompt': prompt} if is_request else None
        if command == '/voice' and job is not None:
            self.media.record_voice_request(identifier, job, reuse=reuse_voice)
        outcome = self.store.consume(identifier, job, max_pending=self.max_pending)
        if outcome == 'duplicate':
            return []
        if outcome == 'busy':
            return [(chat['id'], 'Senai is busy; its request queue is full. Try again after /status.')]
        if outcome == 'queued':
            if self.acknowledge is not None:
                return [(chat['id'], self.acknowledge())]
            return [(chat['id'], f'Queued request #{identifier}. Use /status to check progress.')]
        if voice_error is not None:
            response = voice_error
        elif command == '/status':
            jobs = self.store.recent(chat['id'])
            response = '\n'.join(f'Request #{job["id"]}: {job["status"]}' for job in jobs) or 'No requests yet.'
        elif command == '/session':
            session_id = self.store.shared_session()
            response = f'Shared Codex session: {session_id}' if session_id else 'The shared session will be created by the first request.'
        elif command == '/result':
            job = self.store.latest_completed(chat['id'])
            response = result_text(job) if job else 'No completed result yet. Use /status.'
        elif len(prompt) > 8000:
            response = 'Request is too long; use at most 8000 characters.'
        elif command in ('', '/start', '/help', '/run'):
            response = HELP
        else:
            response = 'Unknown command.\n' + HELP
        return [(chat['id'], response)]
