# Handoff: integrations

Implement this workstream in WSL Ubuntu-22.04.

- Assigned folder: /home/rk/SentiensHermes/senai-integrations
- Assigned branch: feature/integrations
- Repository: senai, a Python 3.10+ wrapper around installed Codex CLI.
- Environment: /home/rk/SentiensHermes/senai-integrations/.venv
- Progress directory: projectprogress/workstreams/integrations/
- Existing features: code writing/editing, Codex options/native modes, Telegram pairing,
  protected setup, durable jobs, and one shared persistent Codex session.
- Baseline: 126 offline tests passed before this parallel setup.

## Your task

Build extensible tool/messaging integrations for senai, starting with Telegram compatibility
and then Discord. The current Telegram adapter already has local pairing, durable jobs,
private result routing, and a persistent shared Codex session. It must keep working.

Ownership: senai/integrations/**, senai/telegram/**, tests/integrations/**,
projectprogress/workstreams/integrations/**, and requirements-integrations.txt if needed.

Targets in small commits:
1. Define/test a minimal transport-adapter boundary for incoming requests, authorization,
   stable request/session identity, and outbound delivery. Reuse the existing queue/executor.
2. Adapt Telegram incrementally without deleting old DBs or changing shared-session semantics.
3. Add a Discord adapter using official API/library documentation, explicit authorized
   user/channel rules, duplicate handling, bounded jobs, and long-reply handling.
4. Add offline contract tests covering both transports, unauthorized requests, failures,
   duplicate updates, reconnects, and cross-platform identity/session policy.

First milestone: failing adapter-contract tests, then a working Telegram-compatible adapter.
Discord live testing needs the user's app/token/channel setup later; do not request secrets
in chat or treat unavailable credentials as an excuse to skip offline implementation.
Do not run the production Telegram bot or use /home/rk/SentiensHermes as a test project.
Research additional platforms only after these boundaries work; do not claim every platform
is integrated. Preserve the existing deliberate shared-session policy and document new
cross-platform scope decisions instead of silently sharing or isolating context.

## Working rules

- Use only your assigned WSL worktree and branch; never edit the Windows mirror or another checkout.
- Read AGENTS.md, projectprogress/parallel/README.md, execution-contract.md, main task.md,
  and the current architecture before coding. Synced/reference material is read-only.
- Activate .venv and use its python/pip/senai. Never reinstall senai globally or use pip --user.
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
cd /home/rk/SentiensHermes/senai-integrations
source .venv/bin/activate
git branch --show-current
python -c 'import senai, sys; print(sys.executable); print(senai.__file__)'
python -m unittest discover -s tests -v
```

Begin scoped implementation after verifying these paths. Do not ask again whether to start.
