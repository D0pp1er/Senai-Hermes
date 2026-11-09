"""Feature-owned Telegram conversations; parsing and schedule creation are injected."""

from datetime import datetime, timezone as utc_timezone
import json
import math
from pathlib import Path
import sqlite3
import threading
import uuid
from zoneinfo import ZoneInfo

from ..integrations.telegram import parse_private_update
from .conversation_state import ConversationState

__all__ = ['ConversationRouter', 'DraftFieldError', 'create_conversation_router', 'bind_schedule_creator']

PROMPTS = {
    'name': 'Name: What should this reminder be called? Use a unique name of 1-80 characters, for example Tea break. /cancel stops setup.',
    'task': 'Task: What should Senai do? For example Remind me to make tea. Use 1-8000 characters. /cancel stops setup.',
    'when': 'When: Pick a future time. Try today at 10pm, tomorrow at 1 am, 10 november 2pm, in 2 minutes, or an ISO timestamp with offset. /cancel stops setup.',
    'repeat': 'Repeat: How often? For example once, daily, or every 2 hours. /cancel stops setup.',
}
SPEC_FIELDS = {'name', 'prompt', 'at', 'timezone', 'every', 'cron', 'misfire', 'grace_seconds', 'retries', 'retry_delay'}


class DraftFieldError(ValueError):
    """A safe validation rejection certifying that no schedule was created."""
    def __init__(self, field, message=''):
        self.field = field if field in PROMPTS else 'when'
        self.message = message
        super().__init__(field)


def bind_schedule_creator(store, *, project, authorize_target, scope='telegram-shared'):
    """Adapter for the already merged cron Store; never starts a worker."""
    project = str(Path(project).expanduser().resolve())
    def create(spec, *, target, request_key):
        authorize_target(target)
        if target.get('project') != project or target.get('scope') != scope:
            raise PermissionError('Destination does not match the configured project.')
        try:
            return store.create(**spec, project=project, scope=scope, delivery_target=target)
        except sqlite3.IntegrityError:
            raise DraftFieldError('name', 'Name already used.') from None
        except (ValueError, TypeError) as error:
            message = str(error).lower()
            field = next((field for token, field in (('name', 'name'), ('prompt', 'task'), ('cron', 'repeat'),
                         ('every', 'repeat'), ('retry', 'repeat')) if token in message), 'when')
            raise DraftFieldError(field) from None
    return create


class ConversationRouter:
    def __init__(self, base_router, *, project, account, parse_schedule=None,
                 create_schedule=None, advanced_handler=None, timezone='Asia/Dhaka',
                 clock=None, draft_ttl=600, new_session_users=(), session_guard=None):
        self.base, self.store, self.username = base_router, base_router.store, base_router.username
        self.project = str(Path(project).expanduser().resolve())
        if not isinstance(account, str) or not account.isascii() or not account.isdecimal():
            raise ValueError('A verified bot account is required.')
        self.account = account
        ZoneInfo(timezone)
        if type(draft_ttl) is not int or not 30 <= draft_ttl <= 3600:
            raise ValueError('Draft lifetime must be 30-3600 seconds.')
        self.timezone, self.ttl = timezone, draft_ttl
        self.clock = clock or (lambda: datetime.now(utc_timezone.utc))
        self.parse_schedule, self.create_schedule = parse_schedule, create_schedule
        self.advanced_handler = advanced_handler
        self.new_session_users, self.session_guard = frozenset(new_session_users), session_guard
        self.state = ConversationState(self.store.path.parent / 'conversations.sqlite3',
                       {'project': self.project, 'account': account})
        self._lock = threading.RLock()

    def is_authorized(self, user):
        return self.base.is_authorized(user)

    def _now(self):
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('Conversation clock must return an aware datetime.')
        return now

    def _new_draft(self, kind):
        return {'id': uuid.uuid4().hex, 'kind': kind, 'phase': 'name',
                'expires': self._now().timestamp() + self.ttl}

    def _target(self, user, chat):
        return {'platform': 'telegram', 'account': self.account, 'project': self.project,
                'scope': 'telegram-shared', 'user_id': user, 'chat_id': chat}

    @staticmethod
    def _field_text(field, text):
        limit = 80 if field == 'name' else 8000
        if not isinstance(text, str) or not text or len(text) > limit or (field == 'name' and '\n' in text):
            raise DraftFieldError(field)
        return text

    def _validated_spec(self, value):
        if not isinstance(value, dict) or set(value) - SPEC_FIELDS:
            raise DraftFieldError('when')
        spec = dict(value)
        spec['name'] = self._field_text('name', spec.get('name', ''))
        spec['prompt'] = self._field_text('task', spec.get('prompt', ''))
        try:
            at = spec['at']
            if isinstance(at, str):
                at = datetime.fromisoformat(at)
            if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None or at <= self._now():
                raise ValueError()
            ZoneInfo(spec.setdefault('timezone', self.timezone))
        except (ValueError, TypeError, KeyError):
            raise DraftFieldError('when') from None
        spec['at'] = at.isoformat()
        every, cron = spec.get('every'), spec.get('cron')
        if every is not None and (type(every) is not int or every < 1):
            raise DraftFieldError('repeat')
        if cron is not None and (not isinstance(cron, str) or len(cron) > 256 or len(cron.split()) != 5):
            raise DraftFieldError('repeat')
        if every is not None and cron is not None:
            raise DraftFieldError('repeat')
        if cron is not None:
            from ..cron.calendar import next_after
            try:
                due = next_after(cron, spec['timezone'], at.timestamp() - 0.000001)
                spec['at'] = datetime.fromtimestamp(due, utc_timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError):
                raise DraftFieldError('repeat') from None
        if spec.get('misfire', 'skip') not in ('skip', 'coalesce'):
            raise DraftFieldError('repeat')
        for field, default, lower, upper in (('grace_seconds', 120, 0, 86400), ('retries', 0, 0, 10)):
            item = spec.setdefault(field, default)
            if type(item) is not int or not lower <= item <= upper:
                raise DraftFieldError('repeat')
        retry_delay = spec.setdefault('retry_delay', 60)
        if isinstance(retry_delay, bool) or not isinstance(retry_delay, (int, float)) or not math.isfinite(retry_delay) or retry_delay < 1:
            raise DraftFieldError('repeat')
        spec.setdefault('misfire', 'skip')
        return spec

    def _resolve(self, draft, repeat):
        if not repeat or len(repeat) > 256:
            raise DraftFieldError('repeat')
        reference = datetime.fromisoformat(draft['reference'])
        value = self.parse_schedule(draft['when'], repeat, now=reference, timezone=self.timezone)
        if not isinstance(value, dict) or set(value) - {'at', 'timezone', 'every', 'cron'}:
            raise DraftFieldError('when')
        if value.get('timezone', self.timezone) != self.timezone:
            raise DraftFieldError('when')
        return self._validated_spec({'name': draft['name'], 'prompt': draft['task'], **value})

    def _preview(self, draft):
        spec = draft['spec']
        at = datetime.fromisoformat(spec['at']).astimezone(ZoneInfo(spec['timezone']))
        repeat = draft.get('repeat') or (('cron ' + spec['cron']) if spec.get('cron') else
                 ('every ' + str(spec['every']) + ' seconds' if spec.get('every') else 'once'))
        return (f"Name: {spec['name']}\nTask: {spec['prompt']}\nWhen: {at:%Y-%m-%d %H:%M:%S} ({spec['timezone']})"
                f"\nRepeat: {repeat}\nDestination: this private chat"
                f"\nIf late: {spec['misfire']}; grace {spec['grace_seconds']} seconds; retries {spec['retries']}"
                "\nReply Confirm to create, or /cancel. Nothing is scheduled yet.")

    def _advanced(self, update, chat, argument):
        action = argument.split(maxsplit=1)[0] if argument else 'help'
        hints = {'edit': 'Edit: review /cron show ID, then use /cron edit ID REVISION {"prompt":"new task"}. A changed revision needs a fresh review.',
                 'show': 'Show: use /cron list in this chat, then /cron show ID.',
                 'pause': 'Pause: use /cron list, then /cron pause ID for a schedule owned by this chat.',
                 'resume': 'Resume: review /cron show ID, then /cron resume ID.',
                 'delete': 'Delete: review /cron list, then /cron delete ID for your schedule.'}
        help_text = hints.get(action, 'Use /cron create for guided setup, /cron list, or /cron help for advanced commands.')
        if self.advanced_handler is None:
            if self.store.consume(update['update_id']) == 'duplicate':
                return []
            return [(chat, help_text)]
        try:
            results = self.advanced_handler(update)
            return [(target, help_text if 'Cron command rejected;' in text else text) for target, text in results]
        except (ValueError, TypeError, KeyError, PermissionError, sqlite3.Error):
            return [(chat, help_text)]

    def handle(self, update):
        with self._lock:
            return self._handle(update)

    def _handle(self, update):
        parsed = parse_private_update(update)
        if parsed is None:
            return self.base.handle(update)
        identifier, user, chat, text = parsed
        text = text.strip()
        parts = text.split(maxsplit=1)
        command, _, mention = (parts[0] if parts and text.startswith('/') else '').partition('@')
        argument = parts[1].strip() if command and len(parts) > 1 else ''
        if mention and mention.lower() != self.username:
            return self.base.handle(update)
        if not self.is_authorized(user):
            self.state.delete(user, chat)
            self.store.consume(identifier)
            return []
        draft = self.state.get(user, chat)
        if command == '/cron' and argument.partition(' ')[0] != 'create':
            return self._advanced(update, chat, argument)
        special = command in ('/cron', '/cancel', '/new')
        if command and not special:
            results = self.base.handle(update)
            if command in ('/help', '/start'):
                return [(target, response + '\n/cron create - guided reminder setup\n/new - request a fresh shared conversation (local policy applies)\n/cancel - cancel your current draft') for target, response in results]
            return results
        active = draft is not None and draft['phase'] != 'done'
        if not special and not active and not (draft and text.lower() == 'confirm'):
            return self.base.handle(update)
        if self.store.consume(identifier) == 'duplicate':
            return []
        now = self._now()
        expired = draft is not None and draft['expires'] <= now.timestamp()
        if expired:
            self.state.delete(user, chat)
            draft = None
        if command == '/cancel' or (active and text.lower() == 'cancel'):
            if draft and draft['phase'] == 'creating':
                return [(chat, 'Creation may already be in progress. Review /cron list before starting again.')]
            self.state.delete(user, chat)
            return [(chat, 'Draft cancelled. Nothing else was changed.')]
        if command == '/new':
            return [(chat, 'Fresh conversations are not enabled yet; ask the local operator.')]
        if command == '/cron':
            if draft and draft['phase'] != 'done':
                return [(chat, 'You already have a draft. Finish it or /cancel before starting another.')]
            if self.create_schedule is None or (not argument.partition(' ')[2].strip() and self.parse_schedule is None):
                return [(chat, 'Guided scheduling is not connected yet. Ask the local operator to connect the cron parser and destination.')]
            draft = self._new_draft('cron')
            payload = argument.partition(' ')[2].strip()
            if payload:
                try:
                    draft['spec'] = self._validated_spec(json.loads(payload))
                    draft['phase'] = 'confirm'
                except (ValueError, TypeError, KeyError):
                    return [(chat, 'JSON create needs name, prompt and a future aware at timestamp, with optional timezone/every/cron. Example: /cron create {"name":"Tea","prompt":"Make tea","at":"2030-11-10T09:00:00+06:00"}. Nothing was created.')]
            self.state.put(user, chat, draft)
            return [(chat, self._preview(draft) if payload else PROMPTS['name'])]
        if expired:
            return [(chat, 'Your draft expired. Start again with /cron create or /new. Nothing was created.')]
        if draft is None:
            return [(chat, 'No active draft. Use /cron create, or send a normal request.')]
        phase = draft['phase']
        if phase in ('creating', 'uncertain'):
            return [(chat, 'The previous creation outcome is uncertain. Review /cron list before /cancel or starting again. It will not be retried automatically.')]
        if phase == 'done':
            return [(chat, 'That schedule was already created. Use /cron list to review it.')]
        try:
            if phase == 'name':
                draft['name'] = self._field_text('name', text)
                draft['phase'] = 'task'
            elif phase == 'task':
                draft['task'] = self._field_text('task', text)
                draft['phase'] = 'when'
            elif phase == 'when':
                if not text or len(text) > 256:
                    raise DraftFieldError('when')
                draft['when'], draft['reference'] = text, now.isoformat()
                try:
                    self._resolve(draft, 'once')
                except DraftFieldError:
                    raise
                except (ValueError, TypeError, KeyError):
                    raise DraftFieldError('when') from None
                draft['phase'] = 'repeat'
            elif phase == 'repeat':
                try:
                    draft['spec'] = self._resolve(draft, text)
                except DraftFieldError:
                    raise
                except (ValueError, TypeError, KeyError):
                    raise DraftFieldError('repeat') from None
                draft['repeat'], draft['phase'] = text, 'confirm'
            elif phase == 'confirm':
                if text.lower() != 'confirm':
                    return [(chat, self._preview(draft))]
                if datetime.fromisoformat(draft['spec']['at']) <= now:
                    raise DraftFieldError('when')
                if not self.state.claim_confirmation(user, chat, draft['id']):
                    return [(chat, 'This confirmation is already being handled. Review /cron list.')]
                if not self.is_authorized(user):
                    self.state.delete(user, chat)
                    return []
                try:
                    spec = dict(draft['spec'])
                    spec['at'] = datetime.fromisoformat(spec['at'])
                    created = self.create_schedule(spec, target=self._target(user, chat),
                                 request_key=f'telegram:{self.account}:{user}:{draft["id"]}')
                    if not isinstance(created, str) or not created:
                        raise RuntimeError('Creation was not confirmed.')
                except DraftFieldError:
                    raise
                except Exception:
                    draft['phase'] = 'uncertain'
                    self.state.put(user, chat, draft)
                    return [(chat, 'Could not confirm the creation outcome. Review /cron list; this draft will not create another schedule automatically.')]
                draft['phase'], draft['created'] = 'done', created
                self.state.put(user, chat, draft)
                return [(chat, f'Created {spec["name"]}. Results will return to this private chat.')]
        except DraftFieldError as error:
            draft['phase'] = error.field
            self.state.put(user, chat, draft)
            return [(chat, PROMPTS[error.field])]
        self.state.put(user, chat, draft)
        return [(chat, self._preview(draft) if draft['phase'] == 'confirm' else PROMPTS[draft['phase']])]


def create_conversation_router(base_router, **kwargs):
    return ConversationRouter(base_router, **kwargs)
