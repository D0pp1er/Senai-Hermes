# Handoff: memory

Implement this workstream in WSL Ubuntu-22.04.

- Assigned folder: /path/to/workspace/senai-memory
- Assigned branch: feature/memory
- Repository: senai, a Python 3.10+ wrapper around installed Codex CLI.
- Environment: /path/to/workspace/senai-memory/.venv
- Progress directory: projectprogress/workstreams/memory/
- Existing features: code writing/editing, Codex options/native modes, Telegram pairing,
  protected setup, durable jobs, and one shared persistent Codex session.
- Baseline: 126 offline tests passed before this parallel setup.

## Your task

Build a Hermes-inspired persistent memory layer above the existing Codex CLI wrapper.
This must remember useful facts across fresh conversations, not merely resume native chats.

Ownership: senai/memory/**, tests/memory/**, projectprogress/workstreams/memory/**,
and requirements-memory.txt if needed.

Targets in small commits:
1. Persist explicit memory entries with IDs, provenance, timestamps, project/scope namespace,
   and add/list/update/delete operations. Start with the standard library where practical.
2. Retrieve relevant entries and construct a bounded context snapshot. Keep memory content
   distinguishable from user instructions; do not blindly promote arbitrary text to policy.
3. Inject context through a feature-local wrapper/injectable executor; record a minimal
   proposed shared hook for later coordinator integration rather than editing core prompts.py.
4. Add a controlled path for extracting candidate facts from completed outcomes, with clear
   validation/deletion/capacity behavior. Never silently retain credentials or cross scopes.

First verifiable milestone: a fact survives process/store restart and is retrieved for a
fresh request in the same project; another project does not see it. Test CRUD, budgets,
corrupt data, concurrent access, relevance, deletion, and scope isolation.
Consult official Hermes memory documentation and disclose which subset is implemented.
An embedding service/vector database is optional, not the starting requirement. Existing
Telegram's shared Codex conversation must not be mistaken for project memory or modified here.

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
cd /path/to/workspace/senai-memory
source .venv/bin/activate
git branch --show-current
python -c 'import senai, sys; print(sys.executable); print(senai.__file__)'
python -m unittest discover -s tests -v
```

Begin scoped implementation after verifying these paths. Do not ask again whether to start.
