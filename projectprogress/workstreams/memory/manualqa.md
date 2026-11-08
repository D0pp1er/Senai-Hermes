# Memory manual QA

Date: 2026-11-09. Run commands from the assigned WSL checkout.

## Offline automated evidence

- Baseline: 126 tests passed before feature work.
- Red/green storage: missing module -> 7 passing behavior tests.
- Red/green snapshots: missing context module -> 12 passing behavior tests.
- Red/green candidates/CLI: missing modules -> 18 passing memory tests.
- Final: .venv/bin/python -m unittest discover -s tests -q -> 144 passed.
- git diff --check -> PASS.
- From /tmp, absolute .venv Python imports senai from this worktree -> PASS.

Coverage: fresh child-process recall, scope/project isolation, CRUD/timestamps, duplicate
and capacity rollback, concurrent writers, corrupt DB preservation, budgets/relevance,
escaped context, snapshot immutability, executor kwargs, blank request rejection,
verified/approved candidate gating, credential-pattern rejection, CLI subprocess CRUD
and outputs symlink rejection.

## Disposable subprocess manual check

PASS: synthetic invoice fact added through one CLI process and recalled by another.
Private scope list empty. Delete followed by fresh list empty. Used a temporary project
under outputs/qa-project; fixture removed after check. Evidence: outputs/qa-project/memory-qa.json.
No production state, network model calls, Telegram poller or schedules were used.

Repeat a visible check with synthetic facts:

    mkdir -p outputs/qa-project/memory-demo
    .venv/bin/python -m senai.memory --project outputs/qa-project/memory-demo --scope qa add 'Invoices use PostgreSQL' --provenance manual
    .venv/bin/python -m senai.memory --project outputs/qa-project/memory-demo --scope qa context invoices
    .venv/bin/python -m senai.memory --project outputs/qa-project/memory-demo --scope private list

Expected: context contains the saved fact; private list is [].
Use the returned ID with delete ID in scope qa; subsequent context is empty.
Use update ID 'replacement fact' --provenance manual for explicit revision.

Live Codex/Telegram checks: NOT RUN. Shared integration has not been wired.
