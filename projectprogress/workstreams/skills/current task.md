# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Learning step 4 implemented: explicit latest-pass-gated activation, accepted version snapshots, durable import/activation/rollback audit and rollback to intact previously accepted packages. Eleven tests first failed on missing APIs, then passed. All 42 feature tests pass. No automatic Codex review or normal CLI wiring is claimed.

Next TDD step: feature-local CLI/demo so users can import a permanent fixture into outputs/skills, list/view saved skills, inspect revisions/history, and demonstrate activation/rollback from terminal. A later injected Codex reviewer creates proposals; broaden import metadata and public sources after validation tests. Coordinator must wire normal senai/Telegram execution; no shared files edited here.

Read MERGE_POLICY.md before each new implementation step. Run ownership/full-suite checks before commit; keep delivery draft until all required evidence and final --ready validation exist. Production usage requires coordinator integration and isolated live end-to-end acceptance.
