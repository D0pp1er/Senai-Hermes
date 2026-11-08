"""Feature-local management and non-executing due preview."""
import argparse
import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from .store import Store, timestamp


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m senai.cron')
    parser.add_argument('--project', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    for flag in ('name', 'prompt', 'scope', 'at'):
        create.add_argument('--'+flag, required=True)
    create.add_argument('--delivery-target', type=json.loads, help='JSON destination object; adapter must authorize it')
    create.add_argument('--timezone', default='Asia/Dhaka')
    recurrence = create.add_mutually_exclusive_group()
    recurrence.add_argument('--every', type=int, help='elapsed seconds; omit for one-shot')
    recurrence.add_argument('--cron', help='five-field expression in --timezone; starts at/after --at')
    create.add_argument('--misfire', choices=('coalesce', 'skip'), default='coalesce',
                        help='default coalesce; choose skip for time-sensitive reminders')
    create.add_argument('--grace-seconds', type=int, default=120,
                        help='skip lateness threshold, inclusive (0..86400; default 120)')
    create.add_argument('--retries', type=int, default=0)
    create.add_argument('--retry-delay', type=int, default=60)
    for command in ('list', 'runs', 'deliveries', 'misfires', 'dry-run'):
        sub.add_parser(command)
    for command in ('pause', 'resume', 'delete', 'interrupt'):
        sub.add_parser(command).add_argument('id')
    args = parser.parse_args(argv)
    try:
        project = args.project.resolve(strict=True)
        if not project.is_dir():
            raise ValueError('project must be a directory')
        store = Store(project/'outputs/.senai-cron/cron.db')
        if args.command == 'create':
            result = store.create(name=args.name, prompt=args.prompt, scope=args.scope,
                at=datetime.fromisoformat(args.at), project=project, timezone=args.timezone,
                every=args.every, retries=args.retries, retry_delay=args.retry_delay, delivery_target=args.delivery_target,
                cron=args.cron, misfire=args.misfire, grace_seconds=args.grace_seconds)
        elif args.command == 'list':
            result = store.list()
        elif args.command == 'misfires':
            result = store.misfires()
        elif args.command == 'deliveries':
            result = store.deliveries()
        elif args.command == 'runs':
            result = store.runs()
        elif args.command == 'dry-run':
            now = timestamp(store.clock())
            active = {r['schedule_id'] for r in store.runs() if r['status'] in ('running', 'retry')}
            candidates = [s for s in store.list() if s['enabled'] and
                s['next_due'] is not None and s['next_due'] <= now and s['id'] not in active]
            would_skip = [s for s in candidates if s['misfire']=='skip' and now-s['next_due']>s['grace_seconds']]
            result = {'due': [s for s in candidates if s not in would_skip], 'would_skip': would_skip,
                'retries': [r for r in store.runs() if r['status']=='retry' and r['ready_at']<=now
                    and any(s['id']==r['schedule_id'] and s['enabled'] for s in store.list())]}
        else:
            getattr(store, args.command)(args.id)
            result = {'status': args.command, 'id': args.id}
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
