"""Pure drafts shared by terminal/chat adapters; persistence needs explicit confirmation."""
from dataclasses import dataclass
from datetime import datetime
import json
import re
from zoneinfo import ZoneInfo
from .calendar import next_after
from .when import parse_when, TimeClarification


@dataclass(frozen=True, init=False)
class Destination:
    key: str
    label: str
    scope: str
    execution_hint: str
    _target_json: str

    def __init__(self, key, label, scope, target, execution_hint):
        if not all(isinstance(x,str) and x.strip() for x in (key,label,scope,execution_hint)):
            raise ValueError('A destination needs a name, scope and truthful execution instructions.')
        if not isinstance(target,dict) or not target:
            raise ValueError('A destination needs an adapter-provided delivery target.')
        for name,value in dict(key=key,label=label,scope=scope,execution_hint=execution_hint,
                               _target_json=json.dumps(target,allow_nan=False)).items():
            object.__setattr__(self,name,value)

    @property
    def target(self):
        return json.loads(self._target_json)


@dataclass(frozen=True)
class ScheduleDraft:
    name: str
    prompt: str
    at: datetime
    timezone: str
    recurrence: str
    destination: Destination
    every: int | None = None
    cron: str | None = None


def build_draft(*, name, prompt, when, recurrence, destination, now, timezone, parser=parse_when):
    if not all(isinstance(value,str) and value.strip() for value in (name,prompt)):
        raise ValueError('Enter a name and task before choosing the schedule.')
    if not isinstance(destination,Destination):
        raise ValueError('Choose an available delivery destination with an execution path.')
    at = parser(when,now=now,timezone=timezone)
    if not isinstance(at,datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError('The time parser must return an aware datetime.')
    # Also validate injected parser results and normalize them into the selected timezone.
    at = parse_when(at.isoformat(),now=now,timezone=timezone)
    if not isinstance(recurrence,str):
        raise ValueError('Choose once, daily, weekly, or every 2 hours.')
    recurrence = recurrence.strip().lower()
    every, cron = None, None
    interval = re.fullmatch(r'every (\d+) (seconds?|minutes?|hours?|days?|weeks?)',recurrence)
    if recurrence == 'once':
        pass
    elif interval:
        count,unit = interval.groups()
        every = int(count)*{'second':1,'minute':60,'hour':3600,'day':86400,'week':604800}[unit.rstrip('s')]
        if not 0 < every <= 366*86400:
            raise ValueError('Use a positive repeat interval up to 366 days.')
    elif recurrence in ('daily','weekly'):
        if at.second or at.microsecond:
            raise ValueError('For daily/weekly repeats choose a whole-minute first time, such as tomorrow at 1am.')
        if at.fold:
            raise TimeClarification('Calendar repeats use the earlier DST occurrence. Choose once for this later offset.')
        day = '*' if recurrence=='daily' else str((at.weekday()+1)%7)
        cron = f'{at.minute} {at.hour} * * {day}'
    elif recurrence.startswith('cron '):
        cron = recurrence[5:]
    else:
        raise ValueError('Choose once, daily, weekly, every 2 hours, or cron 0 9 * * *.')
    if cron:
        due = next_after(cron,timezone,at.timestamp()-0.000001)
        at = datetime.fromtimestamp(due,ZoneInfo(timezone))
    return ScheduleDraft(name.strip(),prompt.strip(),at,timezone,recurrence,destination,every,cron)


def preview_draft(draft):
    return (f'Name: {draft.name}\nTask: {draft.prompt}\n'
            f'First run: {draft.at.isoformat(sep=" ")} ({draft.timezone})\n'
            f'Repeat: {draft.recurrence}\nDestination: {draft.destination.label}\n'
            f'Execution: {draft.destination.execution_hint}\n'
            'Missed runs: skip after 120 seconds. Execution retries: none.')


def commit_draft(store, draft, *, project, now, confirmed):
    if confirmed is not True:
        return None
    # Never reinterpret relative input at confirmation time: the previewed instant is fixed.
    at = parse_when(draft.at.isoformat(),now=now,timezone=draft.timezone)
    return store.create(name=draft.name,prompt=draft.prompt,project=project,
        scope=draft.destination.scope,at=at,timezone=draft.timezone,every=draft.every,
        cron=draft.cron,delivery_target=draft.destination.target,misfire='skip',
        grace_seconds=120,retries=0)
