"""Small deterministic time grammar, with no host-clock or locale assumptions."""
import re
from datetime import datetime, timedelta, timezone as utc_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimeClarification(ValueError):
    """The caller should show this message and ask for a clearer future time."""


_MONTHS = {name: index for index, name in enumerate((
    'january', 'february', 'march', 'april', 'may', 'june', 'july',
    'august', 'september', 'october', 'november', 'december'), 1)}
_MONTHS.update({name[:3]: number for name, number in list(_MONTHS.items())})
EXAMPLES = 'Try today at 10pm, tomorrow at 1 am, 10 november 2027 2pm, or in 2 minutes.'


def _localize(wall, zone):
    candidates = {}
    for fold in (0, 1):
        candidate = wall.replace(tzinfo=zone, fold=fold)
        roundtrip = candidate.astimezone(utc_timezone.utc).astimezone(zone)
        if roundtrip.replace(tzinfo=None) == wall:
            candidates.setdefault(candidate.timestamp(), candidate)
    if not candidates:
        raise TimeClarification('That local time does not exist during the DST change. Choose another time.')
    if len(candidates) > 1:
        raise TimeClarification('That time occurs twice during the DST change. Specify an ISO time with UTC offset.')
    return next(iter(candidates.values()))


def _time(text):
    match = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if not match:
        raise TimeClarification('Specify a time such as 2pm or 14:00.')
    hour, minute, meridiem = match.groups()
    hour, minute = int(hour), int(minute or 0)
    if meridiem:
        if not 1 <= hour <= 12:
            raise TimeClarification('Use hours 1 through 12 with am/pm.')
        hour = hour % 12 + (12 if meridiem == 'pm' else 0)
    elif ':' not in text:
        raise TimeClarification('Is that am or pm? Use 1am, 1pm, or 13:00.')
    if hour > 23 or minute > 59:
        raise TimeClarification('Use a valid time, for example 10pm or 22:00.')
    return hour, minute


def parse_when(text, *, now, timezone):
    """Resolve supported future input in an explicit IANA zone, or ask for clarification.

    Yearless month dates use the current local year only; never roll to a new year.
    Relative units are elapsed durations. Naive ISO times use the configured zone.
    Offset-aware ISO times select an unambiguous instant, including a DST fold.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise TimeClarification('An aware current time is required.')
    try:
        zone = ZoneInfo(timezone)
    except (ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        raise TimeClarification('Choose a valid IANA timezone, for example Asia/Dhaka.') from exc
    if not isinstance(text, str) or not text.strip() or len(text) > 256:
        raise TimeClarification(EXAMPLES)
    text = ' '.join(text.strip().split())
    lower = text.lower()
    local_now = now.astimezone(zone)
    try:
        relative = re.fullmatch(r'in (\d+) (seconds?|minutes?|hours?|days?|weeks?)', lower)
        if relative:
            count, unit = relative.groups()
            seconds = int(count) * {'second':1, 'minute':60, 'hour':3600, 'day':86400, 'week':604800}[unit.rstrip('s')]
            if not 0 < seconds <= 366*86400:
                raise TimeClarification('Use a positive delay up to 366 days, or specify a full date and year.')
            result = (now.astimezone(utc_timezone.utc) + timedelta(seconds=seconds)).astimezone(zone)
        elif re.match(r'^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}', text):
            result = datetime.fromisoformat(text.replace('Z', '+00:00').replace('z', '+00:00'))
            result = _localize(result, zone) if result.tzinfo is None else result.astimezone(zone)
        else:
            day = re.fullmatch(r'(today|tomorrow)(?: at)? (.+)', lower)
            named = re.fullmatch(r'(\d{1,2}) ([a-z]+)(?: (\d{4}))?(?: at)? (.+)', lower)
            if day:
                which, clock = day.groups()
                date = local_now.date() + timedelta(days=which == 'tomorrow')
            elif named:
                number, month, year, clock = named.groups()
                if month not in _MONTHS:
                    raise TimeClarification('Use an English month name, for example 10 november 2027 2pm.')
                date = datetime(int(year or local_now.year), _MONTHS[month], int(number)).date()
            else:
                raise TimeClarification(EXAMPLES + ' Include a date and am/pm; numeric dates like 10/11 are ambiguous.')
            hour, minute = _time(clock)
            result = _localize(datetime(date.year, date.month, date.day, hour, minute), zone)
    except TimeClarification:
        raise
    except (ValueError, OverflowError) as exc:
        raise TimeClarification('That date or time is invalid. Include a valid day, month, year and time.') from exc
    if result.timestamp() <= now.timestamp():
        raise TimeClarification('That time has passed. Choose a future time; specify the year if you mean next year.')
    return result
