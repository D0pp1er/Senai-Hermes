# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Ordinary saved-skill request milestone implemented: CLI run NAME REQUEST with additional --skill/--native-skill, optional --model/--read-only and explicit --expect-file checks. Requests use existing Codex wrapper in unique outputs/skill-runs/<id>/workspace; context/resource copies and results/checks/run manifest retained separately. Unchecked successful output stays unverified; model claims never create passing evidence.

Thirteen new offline behavior tests pass. Actual CLI request using imported skill-creator PASSED: generated csv-identifiers/SKILL.md in QA project's outputs/skill-runs/e1da4304dfb841eb84e8b3cf91e30e67/workspace. Explicit file-existence check passed. Independent format/name parse also passed; this does not prove procedure quality. Report outputs/skills-qa/run-live-report.json; format check run-live-format-check.json. Generated skill is an artifact, not automatically imported/activated or labelled learned.

Outcome recording now accepts exact previously accepted digests so a concurrent activation cannot misattribute in-flight execution to a new revision. Never-accepted candidates still cannot receive execution outcomes. No DB migration.

Next: explicit durable imported/learned/unknown origin and evidence-guided acceptance of locally authored skill artifacts; normal CLI/Telegram hooks remain coordinator-owned. Obsidian export LAST. Full work order in workplan.md.

Read MERGE_POLICY.md before each step. Full suite/scope before commit; delivery draft pending final contract and --ready.
