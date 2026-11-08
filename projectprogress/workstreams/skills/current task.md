# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

User reprioritized working demo first; Obsidian export deferred until last. Added explicit `demo --live [--model MODEL]` alongside unchanged default synthetic demo. Six TDD tests cover success, failed regression, no-change, model error, failed held-out reuse with rollback and CLI progress. No export implementation.

Real installed Codex live demo PASSED. Isolated project: outputs/skills-live-demo/run-bv8i5d3a. Baseline lost zeros; candidate passed 4/4 regression checks; held-out reuse preserved 007,000,42 (2/2 checks); original restored; audit retained. Report: outputs/skills-qa/live-demo-report.json. Prompt/response/check artifacts retained under the reported outputs/evaluations directories. This uses a deliberately lossy known fixture, not universal improvement or production integration.

Next: pinned public acquisition and user-task usability, accurate origin/new-skill authoring records, coordinator production integration; Obsidian export LAST. Full order in workplan.md. No normal shared CLI/Telegram hooks changed.

Reread MERGE_POLICY.md before each implementation step; scope/full suite before commits; final delivery remains draft.
