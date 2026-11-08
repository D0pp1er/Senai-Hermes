# Handoff: cron

Implement this workstream in WSL Ubuntu-22.04.

- Assigned folder: /home/rk/SentiensHermes/senai-cron
- Assigned branch: feature/cron
- Repository: senai, a Python 3.10+ wrapper around installed Codex CLI.
- Environment: /home/rk/SentiensHermes/senai-cron/.venv
- Progress directory: projectprogress/workstreams/cron/
- Existing features: code writing/editing, Codex options/native modes, Telegram pairing,
  protected setup, durable jobs, and one shared persistent Codex session.
- Baseline: 126 offline tests passed before this parallel setup.

## Your task

Build a Hermes-inspired durable scheduled-task feature for senai. This is product code,
not a request to create a Codex app automation or install real OS cron jobs now.

Ownership: senai/cron/**, tests/cron/**, projectprogress/workstreams/cron/**,
and requirements-cron.txt if needed.

Targets in small commits:
1. Persist named one-shot and recurring schedules with explicit timezone, task prompt,
   project/scope, and enabled state. Provide create/list/pause/resume/delete operations.
2. Compute due runs using an injected clock and atomically claim them; define restart,
   overlap, missed-run/catch-up, failure, and bounded retry semantics.
3. Invoke an injected executor (or the existing Codex wrapper through a small adapter),
   record durable run results, and expose optional result-delivery callbacks.
4. Add a feature-local CLI/dry-run worker and documentation for later always-on operation.

First milestone: fake-clock tests prove a saved task becomes due after restart and is
claimed once despite competing workers. Test disabled jobs, timezone/DST boundaries,
misfires, failures, overlap, and recovery. Arbitrary external effects cannot be guaranteed
exactly once; document the actual execution semantics.
Use Asia/Dhaka as the initial configurable user timezone, never assume the host timezone.
Do not alter crontab/systemd, start an always-running scheduler, send real scheduled messages,
or consume unbounded Codex usage. Live scheduling will be enabled only in a later explicit step.
Memory/skill/delivery integrations should be callbacks until sibling branches are merged.

## Working rules

- Use only your assigned WSL worktree and branch; never edit the Windows mirror or another checkout.
- Read AGENTS.md, projectprogress/parallel/README.md, execution-contract.md, main task.md,
  and the current architecture before coding. Synced/reference material is read-only.
- Activate .venv and use its python/pip/senai. Activation lasts only for that shell;
  use absolute .venv/bin/python paths or activate again in every new tool call. Never reinstall senai globally or use pip --user.
- Verify git branch --show-current and python -c 'import senai; print(senai.__file__)' first.
- Start with failing behavior tests, implement small increments, refactor, and commit briefly.
- Preserve existing CLI/Telegram behavior and old state. Do not auto-merge, push, deploy,
  publish confidential materials, start production pollers, or install real recurring jobs.
- Use only the permitted ChatGPT/Codex tooling for development; do not add another AI provider.
- No sub-agents are requested. This chat owns one feature.
- Shared core/CLI/packaging/aggregate documentation files are coordinator-owned. Keep needed
  shared patches in your workstream notes and continue independent feature development.
- Expose a feature-local CLI/module and injectable executor where useful; do not replace the
  existing Codex wrapper. Avoid imports of not-yet-merged sibling-feature modules.
- Keep requests/artifacts/state isolated under this worktree's outputs/; no production tokens,
  bot state, memory, native skill installation, or project data may be copied into tests.
- Update objectives.md, acheivements.md, current task.md, architecture.md, and manualqa.md
  in your own workstream documentation directory after meaningful changes.
- Finish with commit IDs, test results, manual checks, limitations, dependency/migration notes,
  and the minimal shared integration changes needed. Keep user messages concise.


## First commands

```bash
cd /home/rk/SentiensHermes/senai-cron
source .venv/bin/activate
git branch --show-current
python -c 'import senai, sys; print(sys.executable); print(senai.__file__)'
python -m unittest discover -s tests -v
```

Begin scoped implementation after verifying these paths. Do not ask again whether to start.
