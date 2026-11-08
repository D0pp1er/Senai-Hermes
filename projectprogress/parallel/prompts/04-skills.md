# Handoff: skills

Implement this workstream in WSL Ubuntu-22.04.

- Assigned folder: /home/rk/SentiensHermes/senai-skills
- Assigned branch: feature/skills
- Repository: senai, a Python 3.10+ wrapper around installed Codex CLI.
- Environment: /home/rk/SentiensHermes/senai-skills/.venv
- Progress directory: projectprogress/workstreams/skills/
- Existing features: code writing/editing, Codex options/native modes, Telegram pairing,
  protected setup, durable jobs, and one shared persistent Codex session.
- Baseline: 126 offline tests passed before this parallel setup.

## Your task

Build skill import, integration, and evidence-based skill revision for senai.
Existing --skill only mentions an installed skill; it is not an importer or learning system.

Ownership: senai/skills/**, tests/skills/**, projectprogress/workstreams/skills/**,
and requirements-skills.txt if needed.

Targets in small commits:
1. Import SKILL.md-style instruction packages into an isolated local registry, preserving
   source/provenance, names, versions, and validation results. Begin with local fixtures;
   add public repository sources only after validation is tested.
2. List/select/load compatible skills through a feature-local interface and an injectable
   execution/context boundary. Preserve native skill invocation instead of replacing it.
3. Record verified outcome traces and propose versioned instruction revisions from success
   and failure. Validate/regression-check candidate revisions before activation; support rollback.
4. Document supported compatibility, dependencies, limitations, and how to demonstrate reuse.

First milestone: import a valid fixture, reject malformed or escaping paths, select its
instructions for a request, and retain its version/provenance after restart.
Test duplicate/conflicting names, archive traversal/symlinks, unsupported metadata, failed
imports without partial activation, revision history, failed candidates, and rollback.
'Relearning' means revising reusable instructions from verified experience, not fine-tuning
Codex weights or promising automatic universal improvement. Do not execute downloaded scripts
on import or modify global ~/.agents/skills or ~/.codex/skills during parallel development.
Use official Hermes/Codex skill references and the applicable skill-creator instructions
if actually authoring reusable Codex skills. Keep learned artifacts in your isolated outputs/.

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
cd /home/rk/SentiensHermes/senai-skills
source .venv/bin/activate
git branch --show-current
python -c 'import senai, sys; print(sys.executable); print(senai.__file__)'
python -m unittest discover -s tests -v
```

Begin scoped implementation after verifying these paths. Do not ask again whether to start.
