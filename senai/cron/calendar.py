"""Calendar matching with explicit, deterministic DST policy."""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def _iterator(expression, base):
    if not isinstance(expression, str) or len(expression) > 256 or len(expression.split()) != 5:
        raise ValueError('cron must contain five fields')
    if not re.fullmatch(r'[0-9a-zA-Z*/ ,\-]+', expression):
        raise ValueError('unsupported cron expression syntax')
    if re.search(r'(?i)\b[rh]\b', expression):
        raise ValueError('random or hashed cron fields are unsupported')
    try:
        from croniter import croniter
    except ImportError as exc:
        raise ValueError('calendar schedules require requirements-cron.txt') from exc
    try:
        return croniter(expression, base, max_years_between_matches=8)
    except (ValueError, KeyError) as exc:
        raise ValueError('invalid cron expression') from exc


def next_after(expression, zone_name, instant):
    """First matching UTC timestamp strictly after instant; fold=0 only, gaps skipped.

    Search is bounded to eight years and 1500 wall candidates (including skipped gaps).
    """
    zone = ZoneInfo(zone_name)
    wall = datetime.fromtimestamp(instant, zone).replace(tzinfo=None)
    iterator = _iterator(expression, wall)
    try:
        for _ in range(1500):
            candidate = iterator.get_next(datetime).replace(tzinfo=zone, fold=0)
            utc = candidate.astimezone(timezone.utc)
            # Round-trip rejects nonexistent local times instead of shifting the reminder.
            if utc.astimezone(zone).replace(tzinfo=None) != candidate.replace(tzinfo=None):
                continue
            if candidate.timestamp() > instant:
                return candidate.timestamp()
    except (ValueError, OverflowError) as exc:
        raise ValueError('cron has no reachable occurrence within eight years') from exc
    raise ValueError('cron calendar search limit exceeded')


def advance(job, now):
    """Return next future instant, due-slot count and whether that count is a lower bound."""
    first = job['next_due']
    if job.get('cron'):
        future = next_after(job['cron'], job['timezone'], now)
        cursor, count = first, 0
        while cursor <= now and count < 1000:
            count += 1
            cursor = next_after(job['cron'], job['timezone'], cursor)
        return future, count, cursor <= now
    if job['every'] is not None:
        count = int((now-first)//job['every'])+1
        return first + count*job['every'], count, False
    return None, 1, False
