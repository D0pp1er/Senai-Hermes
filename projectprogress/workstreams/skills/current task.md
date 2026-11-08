# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Learning step 3 implemented: injected regression checking with durable passed/failed/error attempts. Eight new tests first failed because validate_revision was missing, then passed. All 31 feature tests pass. No passing result activates anything automatically.

Next TDD step: explicit activation gated by latest passing validation for the exact candidate/base digests, stale-base protection, persistent version history and rollback to a previously accepted version. Afterwards add a Codex reviewer/demo and broaden skill import compatibility/public sources.

Read MERGE_POLICY.md before each new implementation step. Scope/full-suite required before commit. Delivery remains draft and final --ready is not yet applicable.
