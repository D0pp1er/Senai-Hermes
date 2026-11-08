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

## Multifile extension verification (2026-11-09)

Code commit: fa0a3c5. PASS: 167 full offline tests, including 31 memory behavior tests
and 10 coordinator policy tests. Exact commit and full verbose output retained at
outputs/qa-project/memory-multifile-tests.log. Scope guard PASS.

Disposable independent CLI processes proposed and approved SOUL.md, USER.md and
MEMORY.md, then loaded all three into a new private session snapshot. Another user's
snapshot excluded the private preference; shared loading excluded USER by default.
PASS evidence: outputs/qa-project/memory-multifile-qa.json. Fixture removed after QA.

Repeat with synthetic content from this WSL worktree:

    mkdir -p outputs/qa-project/profile-demo
    .venv/bin/python -m senai.memory --project outputs/qa-project/profile-demo --scope qa profile-propose MEMORY.md 'Invoices use PostgreSQL' > outputs/qa-project/profile-proposal.json

Inspect the JSON diff before applying:

    .venv/bin/python -m senai.memory --project outputs/qa-project/profile-demo --scope qa profile-apply outputs/qa-project/profile-proposal.json --approve
    .venv/bin/python -m senai.memory --project outputs/qa-project/profile-demo --scope qa session-context invoices

Expected: labeled MEMORY.md source containing the invoice fact.
For USER.md add --user-id alice before the command; include --include-user on
session-context only in an authorized private session. Without that flag USER is absent.
SOUL proposals accept human origin only. Outcome proposals need --origin outcome
--verified plus a separate reviewed --approve. Empty proposed text deletes a file.
Direct file edits are allowed, validated on load, and invalidate pending proposals.

Live model/native session lifecycle/Telegram integration: NOT RUN and not wired here.
