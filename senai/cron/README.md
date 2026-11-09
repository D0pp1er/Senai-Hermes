# Scheduling

## Usage

The coordinator routes `senai cron` to this package. Saved project defaults are applied by
the shared CLI; direct `python -m senai.cron` still needs `--project PROJECT` before the command.
Management never starts a worker.

A configured friendly create flow asks: name, task, first run, repetition, destination,
then confirmation. Enter `/cancel` at any question, answer `no`, or send EOF to stop without
saving. Nothing is persisted until `yes`. There is no default yes.

First-run examples (resolved in the configured IANA timezone, initially Asia/Dhaka):
- `today at 10pm`
- `tomorrow at 1 am`
- `10 november 2pm` (current local year only, shown explicitly in preview)
- `10 november 2027 2pm`
- `in 2 minutes`
- `2027-11-10T14:00:00+06:00`

Yearless dates never silently roll to next year. Past input asks for a future time/year.
Use month names rather than ambiguous numeric dates like 10/11. Include am/pm or a 24-hour
clock with minutes. Naive ISO times use the configured zone. Ambiguous DST wall times require
an explicit ISO offset; nonexistent DST times require a different local time. Relative delays
are elapsed time (a day is 24 hours), including across DST, and are limited to 366 days.
Supported English grammar is deliberately small; this does not use a model or fuzzy parser.

Repeats: `once`, `daily`, `weekly`, `every 2 hours` (also seconds/minutes/days/weeks),
or advanced `cron 0 9 * * *`. Intervals always ask separately when to run first. Daily/weekly
repeats use local wall time and require a whole-minute first time. Calendar repeats skip
nonexistent DST slots and use the earlier repeated occurrence; an explicit later fold is
supported for a one-shot. Preview shows the actual first cron match, not just its lower bound.

### Execution and delivery configuration

The shared CLI supplies authorized Destination options and a matching account-store
factory. One eligible Telegram account is automatic; otherwise select an account, or
use --telegram-account ID. --local explicitly selects advanced local management.
Missing eligible recipients fails clearly without creating an unsendable schedule.
Destination authorization is rechecked at commit, execution and delivery.

Use senai start or senai telegram start for the configured foreground bot/cron service.
Alternatively stop the bot and run senai cron worker --telegram-account ID. Never run
both for the same account/project/session. Local advanced stores require an explicitly
injected executor/delivery adapter; creation alone does not execute anything.
See [operation/recovery](../../docs/cron-recovery.md).

### Advanced compatibility

Existing explicit ISO flags and Store APIs remain available, including historical dates for
operator fixtures/recovery. The friendly parser and wizard always reject past reminders.
Non-TTY creation never prompts: supply complete flags, including scope and a first run:

```bash
senai cron --project PROJECT create --name check --prompt 'Check build' --scope local \
  --when 'in 2 minutes' --every 3600 --misfire skip
senai cron --project PROJECT list
senai cron --project PROJECT show ID
senai cron --project PROJECT edit ID --expected-revision N --prompt 'Updated task'
senai cron --project PROJECT dry-run
senai cron --project PROJECT pause ID
```

The first example preserves the advanced local-store path; it does not provide automatic
local execution/delivery. Choose the coordinator account-store selector and authorized target
for actual account jobs. `--when` uses the configured zone and a current injected clock;
`--at` preserves the advanced ISO path. Both together are rejected. Missing `--at`/`--when`
explains how to set the first run; `--every` sets repetition, not the first execution instant.
Custom execution retries/grace/misfire settings need complete advanced flags. Wizard defaults
are skip after 120 seconds and zero execution retries; these are shown in the preview.

## Architecture

- `when.py`: public `parse_when(text, *, now, timezone) -> aware datetime` and
  `TimeClarification(ValueError)`. No host-zone/locale inference or clock read inside the parser.
- `draft.py`: immutable Destination/ScheduleDraft; pure build/preview and explicit commit.
  Destination target JSON is copied on construction; returned targets are defensive copies.
  Confirmed commit rechecks the fixed previewed instant against a new clock reading.
- `wizard.py`: terminal questions, actionable retries, EOF/cancel, destination selection and
  explicit yes. The store factory is called only after confirmation and time revalidation.
- `__main__.py`: backwards-compatible advanced management plus injectable wizard seams.
  Explicit timezone overrides injected timezone, then saved setup defaults, then Asia/Dhaka.
- `calendar.py` / `store.py`: bounded calendar matching and transactional SQLite state.
  Atomic claims, misfires, revisions and result/outbox transactions are unchanged by this UX.
- `worker.py` / `delivery.py`: injected execution and independent durable delivery.
  Opt-in execution retries can repeat effects. Only certified-not-accepted sends may retry;
  uncertain executions or sends require review. No exactly-once external-effect guarantee.

### Public draft contract for chat adapters

```python
from senai.cron import Destination, build_draft, preview_draft, commit_draft

# Adapter supplies these from pinned, authorized configuration.
destination = Destination('private-chat', 'This private chat', 'telegram-shared',
    authorized_target, 'The configured Telegram worker runs and delivers here.')
draft = build_draft(name=name, prompt=task, when=answer, recurrence=repeat,
    destination=destination, now=clock(), timezone=configured_timezone)
preview = preview_draft(draft)
# Send preview; wait for explicit yes. Do not call commit for an ordinary draft answer.
identifier = commit_draft(store, draft, project=project, now=clock(), confirmed=True)
```

`build_draft` accepts an injectable `parser=parse_when`. Injected parsers must return aware
future datetimes. `commit_draft(..., confirmed=False)` does nothing. A passed first-run time
must be re-entered/reviewed; relative text is never reinterpreted at confirmation.
The adapter owns per-user draft state, timeout, duplicate-update suppression, `/cancel`,
authorization before commit/send, and pinned installation/project/account/session policy.
Draft helpers themselves do not provide idempotent confirmation or remote session handling.
See the workstream integration notes for exact CLI hook signatures and coordinator requests.

### Tests

```bash
.venv/bin/python -m unittest tests.cron.test_when tests.cron.test_draft tests.cron.test_wizard -v
python scripts/test.py
.venv/bin/python scripts/check_workstream_scope.py --feature cron --ready
```

All tests use temporary stores, fake clocks and fake destinations; no live schedules are started.
No schema migration or new dependency is introduced by the friendly scheduling layer.

## Composed Telegram flow

/cron create uses the same parser/draft helpers and asks name, task, time, repeat,
preview, then Confirm or /cancel. It fixes delivery to the authorized private chat.
Drafts expire after ten minutes; valid drafts survive restart. Invalid fields retry,
/status remains a command and duplicate/uncertain confirmations are fenced by durable
conversation state. See [Telegram](../telegram/README.md) and [manual acceptance](../../docs/all-features-demonstration.md).
