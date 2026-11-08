# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Implemented step 1 of learning: durable outcome evidence tied to exact selected skill content. Six new behavior tests first failed on missing Check, then passed. Existing nine registry tests pass.

Next step (TDD): inactive revision proposals linked to outcome IDs, preserving their base digest and supporting files. Then regression validation, activation with stale-base protection, restart persistence, history and rollback. Afterwards add an injected Codex reviewer/demo and broaden skill imports. No candidate can be activated yet because no revision API exists.

Review MERGE_POLICY.md before each new implementation step. Required records now include changes.md, integration-notes.md and draft delivery.json. Shared integration proposals are only in integration-notes.md.
