# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Reviewer step implemented: review_skill(..., reviewer=...) accepts selected observed outcomes and stages evidence-linked proposals or returns no_change. review_with_codex uses the stable run_codex wrapper, read-only options and JSON Schema in a temporary project-local outputs workspace. CLI review NAME --outcome ID [--outcome ID] [--model MODEL] calls it explicitly. No validation/activation happens automatically.

TDD: initial reviewer tests failed on missing review module, then passed. Twelve reviewer tests plus ten CLI tests pass; includes actual run_codex subprocess with fake codex executable and stale-base rejection. Installed codex exec --help advertises required flags. No live model review or real improvement check performed.

Next step: broaden SKILL.md metadata compatibility and public-source imports with validation/provenance tests; add controlled real reuse/evaluation evidence once a suitable local workflow/checker is chosen. Normal execution/Telegram outcome hooks remain coordinator-owned and unapplied. End-to-end production integration still pending.

Reread MERGE_POLICY.md before each implementation step; scope/full suite required before commits. Final delivery remains draft.
