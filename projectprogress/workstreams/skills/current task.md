# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Implemented learning step 2: inactive, persistent instruction-only revision proposals linked to observed passed/failed outcomes for their exact base digest. Original packages and supporting files preserved. Eight tests first failed on missing propose_revision API, then passed. All 23 feature tests pass.

Next step (TDD): injectable candidate regression validation, durable validation results, failed-candidate rejection and stale-base protection. Then explicit activation, restart history and rollback. Finally add injected Codex reviewer/demo and broaden imports. No activation API exists yet; all candidates remain proposed.

Required checks: scope guard and full suite before commits; --ready only after complete draft contract and final evidence. Shared changes remain proposals in integration-notes.md.
