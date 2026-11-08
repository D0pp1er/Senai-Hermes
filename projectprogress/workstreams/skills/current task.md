# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Feature-local CLI/demo implemented. Eight tests first failed on missing senai.skills.cli, then passed. Commands support permanent local import, metadata listing, instruction viewing/context export, outcomes/revisions/validations/versions/history inspection and explicit activation/rollback. No shared router change.

Real offline subprocess demo PASS: retained isolated project in outputs/skills-demo/, synthetic update to v2 then restore v1, independently listed by a new CLI process. Evidence: outputs/skills-qa/cli-demo-report.json and cli-demo-list.json. This is simulated validation, not model improvement evidence.

Next TDD step: injectable Codex reviewer boundary to generate evidence-linked instruction proposals (never activate automatically). Then broaden metadata compatibility and public import adapters; coordinator wiring and real isolated end-to-end verification remain necessary before production claims. No automatic learner or normal senai integration yet.

Reread MERGE_POLICY.md before each implementation step. Run scope/full suite before commits. Final delivery remains draft.
