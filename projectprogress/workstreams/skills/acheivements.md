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
