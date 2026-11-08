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
