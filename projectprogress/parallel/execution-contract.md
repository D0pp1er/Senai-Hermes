# Shared execution boundaries

## Existing public seams (implemented and frozen for parallel feature work)

- senai.prompts.build_prompt(request, *, skills=()) -> str: validates input and adds
  write/edit instructions plus literal installed-skill mentions.
- senai.workspace.prepare_workspace(parent_project) -> pathlib.Path: validates the
  parent and prepares its outputs/ working directory.
- senai.options.CodexOptions: immutable native option configuration, including resume.
- senai.codex.run_codex(prompt, workspace, *, options=None, stdout=None, stderr=None)
  -> str: normal final response or native JSON streaming; failures raise exceptions.
- Telegram currently queues jobs, launches a senai child, captures native thread IDs,
  and resumes one shared conversation per bot/project. Preserve this behavior/state.

A function returning a string is not proof that generated code passed validation.
Native session continuation is not the new durable semantic-memory feature.

## Intended composition (integration design, not new APIs already in the code)

Incoming CLI/platform message or due schedule
 -> authorize/normalize request and explicit project/scope
 -> retrieve bounded relevant memory and select validated installed skills
 -> invoke the existing Codex execution/session machinery
 -> save result/artifacts and deliver to the origin
 -> record verified outcomes and optionally propose skill revisions

For now, feature modules receive an injectable executor/callback. Tests use fakes.
Do not invent incompatible replacement execution engines or duplicate core CLI logic.
Do not import sibling-feature modules before those branches have been integrated.

## Feature contracts to expose and document

- Integrations: normalize incoming platform messages; distinguish account/chat identity,
  project, request ID, and delivery target. Keep authorization outside model prompts.
  Preserve native session identity explicitly, never select another user's chat via --last.
- Memory: explicit namespace derived from canonical project plus requested scope; bounded
  retrieval/snapshot and persistent add/update/delete. Expose context without executing it.
- Cron: durable schedule/run identity and due-job claims; inject clock and executor;
  keep result delivery as an optional callback. Define timezone/misfire/retry policy.
- Skills: local registry with provenance, validation, version/active revision, and outcome
  records. Expose selected instruction text/paths without executing imported code on import.

The coordinator will add the smallest shared request/result and hook interfaces once
feature needs are demonstrated. Proposed changes belong in workstream notes until then.
Do not add hooks to main or shared code from four chats independently.

## Storage and tests

Each worktree owns isolated outputs/ state. Do not extend the same live SQLite DB from
multiple branches. Use feature-specific stores (memory, cron, skills) and migrations
that preserve existing data. Defaults must not silently mix different projects.

All tests belong under tests/<feature>/. Feature progress and manual QA belong under
projectprogress/workstreams/<feature>/. The original baseline has 126 tests; retain them.
This document defines engineering ownership, not a claim of full Hermes feature parity.
