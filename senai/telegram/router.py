"""Authorize private updates before routing text into the durable request queue."""

HELP = (
    'Send a code request as text, or /run your request.\n'
    '/status - latest requests and their states\n'
    '/result - resend your latest completed result\n'
    '/help - show this message\n'
    'Requests are one-off; generated files stay in the configured outputs/. '
    'Only configured private users can execute requests.'
)


def result_text(job):
    return f'Request #{job["id"]}: {job["status"]}\n\n{job["result"]}'


class Router:
    def __init__(self, store, allowed_users, username, *, max_pending=4):
        self.store = store
        self.allowed_users = allowed_users
        self.username = username.lower()
        self.max_pending = max_pending

    def handle(self, update):
        identifier = update.get('update_id') if isinstance(update, dict) else None
        if type(identifier) is not int or identifier < 0:
            return []
        message = update.get('message')
        message = message if isinstance(message, dict) else {}
        sender, chat = message.get('from', {}), message.get('chat', {})
        sender = sender if isinstance(sender, dict) else {}
        chat = chat if isinstance(chat, dict) else {}
        authorized = (
            type(sender.get('id')) is int and sender['id'] in self.allowed_users
            and sender.get('is_bot') is not True and chat.get('type') == 'private'
            and type(chat.get('id')) is int and chat['id'] == sender['id']
        )
        text = message.get('text')
        if not authorized or not isinstance(text, str):
            self.store.consume(identifier)
            return []
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
        prompt = argument if command == '/run' else text
        is_request = (not command or command == '/run') and bool(prompt) and len(prompt) <= 8000
        job = {'chat_id': chat['id'], 'user_id': sender['id'], 'prompt': prompt} if is_request else None
        outcome = self.store.consume(identifier, job, max_pending=self.max_pending)
        if outcome == 'duplicate':
            return []
        if outcome == 'busy':
            return [(chat['id'], 'Senai is busy; its request queue is full. Try again after /status.')]
        if outcome == 'queued':
            return [(chat['id'], f'Queued request #{identifier}. Use /status to check progress.')]
        if command == '/status':
            jobs = self.store.recent(chat['id'])
            response = '\n'.join(f'Request #{job["id"]}: {job["status"]}' for job in jobs) or 'No requests yet.'
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
