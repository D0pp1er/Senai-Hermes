# Cron manual QA
PASS: own .venv Python and senai import both resolve inside senai-cron; branch feature/cron.
PASS: 126 baseline offline tests; eight new feature tests. No live checks performed.
Recovery: stop/verify absence of old workers before calling Store.interrupt(run_id).
Use only outputs/qa-project for state. Never point cron QA at production state.
