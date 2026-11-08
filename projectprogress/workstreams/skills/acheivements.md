# Skills achievements

- Verified feature/skills and this worktree's .venv Python/package binding.
- TDD red: nine behavior tests could not import the missing senai.skills module.
- Green: nine registry behavior tests pass. Valid imports retain source, version, SHA-256 package digest and passed validation after restart.
- Rejected malformed/unknown metadata, duplicate/conflicting names, symlink packages/content, non-directory archive input, missing selections and changed installed content.
- Import copies scripts as inert bytes; nothing is executed or globally installed.
- Full offline regression result recorded in manualqa.md.

- Added outcome records and six red-to-green tests: restart identity, failed-check correction, unverified prose, invalid record atomicity, registry isolation and insertion order. No activation occurs.

- Learning step 2: eight red-to-green tests cover inactive proposal restart, supporting-file preservation, evidence rejection, wrong-skill links, invalid candidate cleanup, duplicate versions, tamper detection and passed-outcome support.

- Learning step 3: eight red-to-green tests verify persisted checking context, failed results, invalid/empty result rejection, sanitized checker exceptions, tamper checks, unknown IDs and retained revalidation history.

- Learning step 4: eleven red-to-green tests cover activation/reuse after restart, missing/failed/error validation gates, latest-failure rejection, stale siblings, candidate tampering, rollback/history, unaccepted targets, damaged current recovery, damaged target rejection, old version uniqueness and idempotent migration.

- CLI milestone: eight red-to-green tests pass, including real `python -m senai.skills --help` in a separate cwd. Direct demo and independent list subprocess passed; retained isolated demo registry shows version 1 after activation/rollback.

- Reviewer adapter: twelve behavior tests pass, including strict malformed-reply handling, exact selected evidence, no-change, no activation/validation, pre-call budget rejection, stale-base protection and actual wrapper subprocess with fake Codex. Two additional CLI review tests pass. Installed required flags verified without live model call.

- Metadata milestone: standard/Hermes-style YAML imported with byte preservation and restart; malformed/unsafe YAML and excessive lengths rejected. Optional declarations preserved through reviewer/activation. New predicate blocks incompatible execution before executor call. PyYAML pin installed only in assigned .venv.

- Recorded revised Obsidian workplan and weighted approximate 60% expanded-scope estimate. Obsidian export/UI and real learned-skill inventory are not implemented or verified yet.

- Working live controlled demo PASSED: actual Codex baseline lost identifier zeros; reviewed instructions passed 4/4 regression checks and 2/2 held-out reuse checks; rollback preserved audit. Six new offline tests cover live-demo control flow and failure gates. Obsidian export deferred by user.

- Public acquisition: thirteen offline tests pass. Real CLI imported openai/skills skill-creator at immutable commit 49f948faa9258a0c61caceaf225e179651397431 into isolated outputs registry; seven preserved files and pinned provenance survived restart. No scripts executed/global state changed.

- Ordinary CLI requests now use exact saved instructions and resources via the existing Codex wrapper. Thirteen behavior tests passed. Real imported skill-creator generated a workspace-local csv-identifiers/SKILL.md; artifact existence and separate format/name checks passed. No automatic registry/learned-origin activation of the generated artifact.
