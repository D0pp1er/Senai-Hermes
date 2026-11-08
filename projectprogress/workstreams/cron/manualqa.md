# Cron manual QA
PASS: own .venv Python and senai import both resolve inside senai-cron; branch feature/cron.
PASS: 126 baseline offline tests; eight new feature tests. No live checks performed.
Recovery: stop/verify absence of old workers before calling Store.interrupt(run_id).
Use only outputs/qa-project for state. Never point cron QA at production state.

Offline CLI verification (no executor invoked):
```
cd /home/rk/SentiensHermes/senai-cron
.venv/bin/python -m senai.cron --project outputs/qa-project create --name demo --prompt 'Offline demo' --scope qa --at 2020-01-01T00:00:00+06:00
.venv/bin/python -m senai.cron --project outputs/qa-project dry-run
.venv/bin/python -m senai.cron --project outputs/qa-project runs
```
Expect demo in due; runs stays empty. Use returned ID with pause/resume/delete.
Store path: <project>/outputs/.senai-cron/cron.db. --at requires an explicit UTC offset;
--timezone records the user's IANA zone. --every is elapsed seconds across DST, not a daily
wall-clock recurrence. No daemon or executor is exposed by this CLI. Later always-on operation
must supply an authorized executor to Worker, call tick in a supervised bounded loop, and
handle shutdown before explicit interrupted-run recovery. Never run overlapping old/replacement
workers during manual recovery. Injected executors receive a run dict with JSON snapshot;
delivery receives the completed durable run. Delivery callbacks must implement their own
idempotency and redelivery if needed. Results/errors may contain private task output: protect
this local database like project data. No real schedules are activated by these commands.

PASS: full offline regression 135 tests. CLI behavior tested in temporary directories.
Documentation example above is a reproducible operator check, not a claimed live run.

Durable-delivery verification: run .venv/bin/python -m unittest tests.cron.test_delivery -v.
All send callbacks use fakes and temporary DBs. Inspect queue with:
.venv/bin/python -m senai.cron --project outputs/qa-project deliveries
No transport/daemon is started. CLI create supports --delivery-target as a JSON object;
this is stored routing data, not proof of permission. Unknown sends require operator review.

Calendar/misfire offline check:
.venv/bin/python -m pip install -r requirements-cron.txt
.venv/bin/python -m unittest tests.cron.test_calendar tests.cron.test_cli -v
Expected: all pass; fakes/temp DBs only. No live execution.
Feature CLI supports --cron '0 9 * * *' --timezone Asia/Dhaka --misfire skip --grace-seconds 120.
Keep --at offset-aware; for calendar schedules it is an inclusive start boundary. dry-run
shows would_skip separately; misfires command shows only already committed skip/coalesce events.
Earlier elapsed-only statements in this QA history describe previous milestones; calendar
behavior is defined in current architecture.md. Source reference for parser usage:
https://github.com/pallets-eco/croniter/blob/main/README.rst .
