# Profile UX helper handoff (current extension)

New user-facing API:
    profile_main(kind, argv, *, installation, stdin, stdout, stderr) -> int
    setup_profiles(installation) -> dict[str, Path]

Both are exported from senai.memory. kind is memory/user/soul. argv is only the
shortcut tail: add [TEXT], show, path, setup. stdout/stderr/stdin are injectable;
TTY prompt uses stdin.isatty and bounded readline; missing non-TTY text fails promptly.
Return codes: 0 success/help/duplicate, 2 usage/validation/storage, 130 cancellation.
No SystemExit leaks from the helper, including subcommand --help.

## Proposed root routing (coordinator only)

Obtain installation from the existing resolved saved defaults/explicit configuration,
then call the helper for human shortcut invocations. No settings are loaded or inferred
by the helper. Do not use it from automatic learning or parse model output into it.

Preserve advanced root memory routes: the existing python -m senai.memory CLI is unchanged,
including SQLite add TEXT --provenance SOURCE and legacy scoped flags. Do not blindly
replace every memory add route: short human add appends MEMORY.md; explicit advanced
commands/flags must keep SQLite behavior. Coordinator owns disambiguation and flags.
user/soul use the same human helper with their corresponding kind. Normal UX requires
no installation/scope/user-ID arguments once setup has saved defaults.

Use setup_profiles during explicit onboarding/setup instead of duplicating file creation.
It creates missing installation folders and empty profiles with private creation modes;
existing contents are validated and preserved. It writes no defaults or SQLite and
returns exact absolute paths. Keep missing configuration errors actionable (senai setup).
Add requires the profile directory already initialized; a missing target file can be
created by the explicit human append. Show/path/help remain read-only.

## Fresh sessions and integrations /new handoff

Edits never mutate a frozen snapshot. Helpers report that a fresh session loads changes.
No CLI/core or Telegram/session files are changed here.

Integration proposal: /new should select a genuinely fresh native execution after the
current active job boundary, omitting the old --resume ID. The existing runtime then
calls InstallationMemory.snapshot and binds the new native ID. Preserve prior native
history and snapshot records. Do not delete profiles/snapshot DBs or reuse the previous
snapshot under a new ID. Confirm the installed root remains pinned to bot startup
configuration. Existing snapshot API is sufficient; memory adds no separate reset API.
Queue/session ownership and exact /new public API remain integrations/coordinator work.
No Telegram /new implementation is claimed by this feature.

## Validation/compatibility

Human append preserves old text, deduplicates case/whitespace-normalized notes,
including multiline notes, and uses the existing revision/atomic-write rules.
Full files fail with an actionable path/shorten message; no eviction.
Automatic SOUL learning stays blocked. Explicit confirmed human soul add uses human
origin; this is the only intended shortcut entry path. Confirmation-only personal
observations and verified-only significant milestone learning are unchanged.

Standalone demo: python -m senai.memory.profile_cli --installation ROOT KIND add TEXT.
Module guide: senai/memory/README.md (Usage and Architecture). No dependency/schema
change, no model/network/service operations, no global settings changes.
Tests include a real subprocess demo and unchanged advanced SQLite add.
New live root-router or Telegram /new acceptance has not been run.

---
Earlier integrated memory/evaluator contracts follow for reference.

> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

# Noteworthy evaluator extension (current handoff)

This extends the already integrated installation runtime; it does not replace it.
User decision: preferences/habits/likes/dislikes require explicit confirmation to retain.
Repeated observations NEVER replace confirmation. Significant choices also require
confirmation; only validator-verified significant milestones may qualify automatically.

New API:
    proposals = evaluate_noteworthy(events, existing={
        "USER.md": runtime.memory.profiles.read("USER.md").text,
        "MEMORY.md": runtime.memory.profiles.read("MEMORY.md").text,
    })

events are MemoryEvent values supplied by trusted app evidence:
- event_id: stable local evidence identifier (max 200 chars, validated).
- kind: preference/habit/like/dislike/choice/milestone; unknown kinds are ignored.
- text: concise single-line fact, max 240 characters.
- source: user for confirmed user facts, validator for checked milestones.
- verified: actual source/result validation, not a model's success assertion.
- confirmed: explicit user approval to retain this user fact, not repetition/inference.
- significant: required for choice and milestone; decided by trusted app validation.

Coordinator callback adaptation (proposal only; core files unchanged):
    def learning(request, response, workspace):
        events = trusted_evidence_for_this_successful_run(request, response, workspace)
        proposals = evaluate_noteworthy(events, existing=current_global_profiles())
        return [LearningDecision(p.name, p.text, noteworthy=p.noteworthy,
                                 verified=p.verified) for p in proposals]

Existing InstallationRuntime.execute(..., learning=learning) saves decisions only
after successful execution. Tests exercise this integrated callback. The coordinator
must implement/choose actual evidence sourcing and the confirmation interaction;
arbitrary uploaded JSON/model output must not populate trusted flags.

The evaluator itself is pure: no DB/file writes, observation history, hidden retention,
classifier service, model calls or import side effects. It returns immutable proposals
with name/text/reason/evidence ID plus noteworthy=True, verified=True.
Targets are USER.md/MEMORY.md only; no SOUL target can be proposed.

Input bound 100 events; default at most 5 candidates and 1200 candidate text characters.
Per-target estimated size cannot exceed the existing 4000-char profile limit.
Known facts and batch duplicates are compared with Unicode normalization, case folding,
whitespace normalization and terminal-period removal, within the same target.
Duplicate event IDs are ignored within a batch. This is not semantic deduplication or
persistent event idempotency. Existing-file checks suppress normal repeat proposals.
Different facts or corrections need existing explicit reviewed edit/delete paths.

Credential-looking, empty, multiline and oversized facts are skipped without echoing
their contents in diagnostics. Malformed decision flags/batch limits raise ValueError.
Budget/capacity skips do not evict or modify existing facts. Final saving revalidates
through InstallationMemory.remember; concurrent changes can still cause a conflict.

Dry run:
    python -m senai.memory --installation QA_ROOT evaluate-events tests/memory/fixtures/noteworthy-events.json

Expected two proposals (confirmed preference + verified milestone), no fact writes.
CLI may initialize normal installation storage/locks while reading current profiles;
the pure function performs no I/O. No new dependencies or schema migration.
This extension does not change interactive chat, Telegram, snapshot lifecycle, shared
core files, or the already integrated explicit remember command.

---
The sections below document the previously integrated installation memory baseline.

# Current memory integration: one owner per installation

This supersedes the earlier multi-user/project-private integration proposal.
User clarified: one senai repo/installation has one user. All its projects and sessions
share USER.md and MEMORY.md. Separate installations remain independent.

## Coordinator hook (proposed, not wired here)

Select one stable, explicit installation root from trusted app configuration.
Do not derive it from the active project, request text, cwd, Python site-packages,
home directory, or bot/chat identity.

    memory = InstallationMemory(configured_installation_root)
    snapshot = memory.snapshot(request)
    result = execute_session(request, task_workspace, snapshot=snapshot,
                             executor=run_codex, options=options, skills=skills)

The task workspace may belong to any project. The installation root stays constant.
New snapshots include SOUL.md, USER.md, MEMORY.md and relevant installation SQLite facts.
Reuse the frozen snapshot during native resume. A fresh session or explicit refresh
rebuilds it. Coordinator still owns native-session snapshot persistence across processes.
Do not change exact native resume IDs or treat chat history as saved semantic memory.

No multi-user routing or private USER exclusion is needed in this single-owner mode.
Do not expose this mode to multiple independent users; legacy scoped APIs remain
available unchanged for compatibility, not as the recommended single-owner design.

## Flat storage and migration

All paths below are relative to the configured installation root:

    outputs/.senai-memory/SOUL.md
    outputs/.senai-memory/USER.md
    outputs/.senai-memory/MEMORY.md
    outputs/.senai-memory/memory.db

USER: stable preferences, habits, likes/dislikes and significant choices.
MEMORY: core events, milestones and noteworthy experiences with the user.
SOUL: explicit human-authored identity/style; automatic learning cannot update it.
SQLite: detailed explicit facts with provenance/timestamps. Fixed namespace is
Namespace(canonical_installation_root, "installation"), shared across task projects.

The SQLite schema remains v1. Existing per-project scopes/hashed profile files remain
untouched and are not silently imported, mixed, deleted or exposed. Any migration of
real old profiles needs explicit source selection and user review. No automatic file/DB
mirroring. InstallationMemory is an additive compatibility adapter.
No global home-directory state or machine-wide memory is introduced.

## App-controlled learning

    memory.remember("USER.md", "Prefers concise responses", user_requested=True)
    memory.remember("MEMORY.md", "Completed the first release",
                    noteworthy=True, verified=True)

user_requested must reflect a real authorized user request.
noteworthy and verified must come from the trusted app decision/validation path.
The app may save these without another approval prompt, per the user's standing request.
Ordinary output and unverified noteworthy claims are rejected. The memory module does
not run an autonomous classifier or equate a model's success text with verification.
Candidate generation/judgment wiring belongs to the coordinator.

remember appends a bounded validated bullet, skips exact duplicate blocks and preserves
existing text. On racing updates it raises ConflictError; retry after rereading. It cannot
edit SOUL. Corrections/deletions/full replacements use existing reviewed propose/apply
APIs (or explicit human edits). All file-size, credential-pattern and conflict rules remain.
No raw transcript retention, silent eviction, automatic compaction or semantic deduplication.

## CLI and verification

Recommended:
    python -m senai.memory --installation REPO remember USER.md 'Prefers Python' --user-requested
    python -m senai.memory --installation REPO session-context hello

No --project, --scope or --user-id is used in installation mode. USER is included by default.
add/list/update/delete/context operate on installation SQLite facts. profile-show,
profile-propose/profile-apply work with the flat global files. SOUL remains human-only.
Legacy --project PROJECT --scope SCOPE mode retains its original behavior.

Standard library only; WSL/POSIX fcntl required. Shared/core files are unchanged.
Coordinator owns shared CLI selection and learning/session adapters. Live wiring unverified.
Limits: files 4000 chars / 16000 UTF-8 bytes, total context 8000 chars default. Curated
overflow fails; relevant SQLite entries fill remaining space. Frozen context cannot
retract deleted facts from existing sessions. Local data unencrypted; pattern-based
secret detection is incomplete. Cooperative locking does not protect against hostile
external filesystem races. Source labels cannot guarantee model instruction compliance.

## Installation memory integration (2026-11-09)

Coordinator update: the proposed hooks above are now wired on main.

Memory is opt-in through one explicit existing installation root:
    export SENAI_INSTALLATION_ROOT=/absolute/path/to/installation
    senai --project /absolute/path/to/project-a "Remember in USER.md: Prefers concise replies"
    senai --project /absolute/path/to/project-b "What response style do I prefer?"

Alternatively pass --installation ROOT on each call. The installation root stays constant across projects; no inference from cwd, home, package location or Telegram identity. One owner per installation only. USER.md and MEMORY.md live at ROOT/outputs/.senai-memory/, alongside human-controlled SOUL.md and memory.db.

Direct management is available as senai memory --installation ROOT remember USER.md "Prefers concise replies" --user-requested. With SENAI_INSTALLATION_ROOT configured, the memory subcommand uses that root automatically.

Fresh execution loads a bounded InstallationMemory snapshot. Native thread.started events bind it in native-snapshots.sqlite3; exact --resume ID reuses that persisted snapshot without rereading changed profiles. --last, ephemeral mode and sessions without a stored snapshot fail clearly rather than silently selecting/rebuilding context. Existing native sessions and old scoped memory are retained and not silently adopted/imported. Unconfigured runs retain the original execution path. Native interactive/pass-through commands do not gain memory injection.

Explicit requests "Remember in USER.md: FACT", "Remember in MEMORY.md: FACT", or "Remember that FACT" are saved after successful execution (the latter defaults to MEMORY.md). Telegram's presentation wrapper is supported when its child inherits the explicitly configured root; no production bot was enabled/restarted for this integration. Automatic SOUL save requests are rejected. App-managed profile instructions are cooperative; this is not a sandbox against hostile filesystem writes.

Trusted app validators can call InstallationRuntime.execute(..., learning=validator). The validator receives (request, successful_response, workspace) and returns LearningDecision objects. A noteworthy event requires noteworthy=True AND verified=True; user_requested must represent real user authorization. Ordinary model output, "Memory:" lines and success text never grant verification or trigger implicit saving. No autonomous noteworthy classifier is introduced. Learning does not refresh an existing session's frozen context.

Integrated feature/memory through 3146de5 in merge 0f0c979. Coordinator lifecycle wiring: 62cbf9f. Feature scope/readiness passed before merge, with 176 offline tests (40 memory tests). Combined regression: 235 passed, including existing Telegram media/auth tests, 40 memory tests and 11 coordinator memory lifecycle tests. TDD logs include failing missing-runtime and SOUL-write tests before implementations.

Real isolated Codex acceptance at 62cbf9f: project A saved a harmless USER.md fact; a distinct fresh session in project B recalled it from the same installation. Exact-ID resume also succeeded. No production bot state, jobs, pairing, sessions or credentials were copied or used; no push, deployment or production restart.

Evidence:
- outputs/memory-combined-regression.log
- outputs/memory-transport-tests.log
- outputs/qa-memory-installation/acceptance.json
- outputs/qa-memory-installation/first-session.jsonl
- outputs/qa-memory-installation/final-fresh-session.jsonl
- outputs/qa-memory-installation/final-resume.jsonl

## Confirmed memory learning (2026-11-09)

Integrated 929a2ea in b6c56f7; successful-outcome evaluator wiring 4ffc1aa. Personal facts require explicit user retention confirmation; repetition never confirms. Only app-verified significant milestones qualify automatically. SOUL.md stays human-controlled. Installation-wide memory and frozen session snapshots preserved. Branch readiness/248 tests and combined 370 tests passed. See projectprogress/memory-learning.md. No push, deployment or production bot state used.
