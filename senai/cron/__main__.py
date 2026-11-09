"""Feature-local management and non-executing due preview."""
import argparse
import json
import sys
import sqlite3
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from .store import Store, timestamp


def main(argv=None, *, store_factory=None, stdin=None, stdout=None, stderr=None,
         clock=None, timezone=None, destinations=()):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    clock = clock or (lambda: datetime.now(dt_timezone.utc))
    parser = argparse.ArgumentParser(prog='python -m senai.cron', epilog='Shared CLI also supports senai cron worker and worker-status with --project and --telegram-account.')
    parser.add_argument('--project', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    for flag in ('name', 'prompt', 'scope'):
        create.add_argument('--'+flag)
    first_run = create.add_mutually_exclusive_group()
    first_run.add_argument('--at', help='advanced ISO first-run instant; includes UTC offset')
    first_run.add_argument('--when', help='friendly future first run, e.g. tomorrow at 1 am or in 2 minutes')
    create.add_argument('--delivery-target', type=json.loads, help='JSON destination object; adapter must authorize it')
    create.add_argument('--timezone', help='IANA zone; defaults to saved configuration, then Asia/Dhaka')
    recurrence = create.add_mutually_exclusive_group()
    recurrence.add_argument('--every', type=int, help='elapsed seconds; omit for one-shot')
    recurrence.add_argument('--cron', help='five-field expression in --timezone; starts at/after --at')
    create.add_argument('--misfire', choices=('coalesce', 'skip'), default=None,
                        help='default coalesce; choose skip for time-sensitive reminders')
    create.add_argument('--grace-seconds', type=int, default=120,
                        help='skip lateness threshold, inclusive (0..86400; default 120)')
    create.add_argument('--retries', type=int, default=0)
    create.add_argument('--retry-delay', type=int, default=60)
    for command in ('list', 'runs', 'deliveries', 'misfires', 'dry-run'):
        sub.add_parser(command)
    sub.add_parser('show').add_argument('id')
    edit = sub.add_parser('edit', argument_default=argparse.SUPPRESS)
    edit.add_argument('id')
    edit.add_argument('--expected-revision', type=int, required=True,
                      help='revision from show; stale changes are rejected')
    for flag in ('name', 'prompt', 'timezone'):
        edit.add_argument('--'+flag)
    edit.add_argument('--at', type=datetime.fromisoformat)
    edit.add_argument('--delivery-target', type=json.loads)
    edit.add_argument('--misfire', choices=('coalesce','skip'))
    for flag in ('grace-seconds','retries','retry-delay'):
        edit.add_argument('--'+flag, type=int)
    edit_recurrence = edit.add_mutually_exclusive_group()
    edit_recurrence.add_argument('--every', type=int)
    edit_recurrence.add_argument('--cron')
    edit_recurrence.add_argument('--once', action='store_true',
                                 help='switch to one-shot; requires --at')
    for command in ('pause', 'resume', 'delete', 'interrupt'):
        sub.add_parser(command).add_argument('id')
    args = parser.parse_args(argv)
    try:
        project = args.project.resolve(strict=True)
        if not project.is_dir():
            raise ValueError('project must be a directory')
        factory = store_factory or (lambda project: Store(project/'outputs/.senai-cron/cron.db'))
        if args.command == 'create':
            from .when import parse_when
            from .wizard import run_wizard
            from senai.defaults import load_defaults
            zone = args.timezone or timezone or load_defaults().get('timezone','Asia/Dhaka')
            first = args.at or args.when
            missing = [flag for flag in ('name','prompt','scope') if getattr(args,flag) is None]
            if first is None:
                missing.append('first run (--when or --at)')
            if missing:
                if not stdin.isatty():
                    raise ValueError('Missing '+', '.join(missing)+'. Non-interactive creation requires flags. '
                        'Supply the first run with --when "in 2 minutes" or --at ISO; --every only sets repetition. '
                        'Run create in a terminal for sequential questions.')
                if args.delivery_target is not None or (args.scope is not None and
                        any(d.scope != args.scope for d in destinations)):
                    raise ValueError('For the wizard, choose an adapter-provided destination instead of scope/target overrides.')
                if (args.retries != 0 or args.retry_delay != 60 or args.grace_seconds != 120
                        or args.misfire not in (None,'skip')):
                    raise ValueError('Custom retry/grace settings require complete advanced flags; wizard uses safe defaults.')
                recurrence = (f'every {args.every} seconds' if args.every is not None else
                              ('cron '+args.cron if args.cron else None))
                run_wizard(project=project,store_factory=factory,stdin=stdin,stdout=stdout,
                    clock=clock,timezone=zone,destinations=destinations,name=args.name,
                    prompt=args.prompt,when=first,recurrence=recurrence)
                return 0
            resolved = (parse_when(args.when,now=clock(),timezone=zone) if args.when is not None
                        else datetime.fromisoformat(args.at))
            store = factory(project)
        else:
            store = factory(project)
        if args.command == 'create':
            result = store.create(name=args.name, prompt=args.prompt, scope=args.scope,
                at=resolved, project=project, timezone=zone,
                every=args.every, retries=args.retries, retry_delay=args.retry_delay, delivery_target=args.delivery_target,
                cron=args.cron, misfire=args.misfire or 'coalesce', grace_seconds=args.grace_seconds)
        elif args.command == 'show':
            result = store.get(args.id)
        elif args.command == 'edit':
            changes = {key: value for key,value in vars(args).items()
                       if key not in ('command','project','id','expected_revision')}
            if changes.pop('once', False):
                changes.update(every=None, cron=None)
            elif 'cron' in changes:
                changes['every'] = None
            elif 'every' in changes:
                changes['cron'] = None
            result = store.update(args.id, expected_revision=args.expected_revision, **changes)
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
        print(json.dumps(result, indent=2),file=stdout)
        return 0
    except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
        print(str(exc), file=stderr)
        return 2
    except KeyboardInterrupt:
        print('Cancelled.',file=stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
