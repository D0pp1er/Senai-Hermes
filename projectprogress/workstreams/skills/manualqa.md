# Skills manual QA

Offline TDD: nine tests first failed with ModuleNotFoundError for senai.skills, then passed with implementation.

Reproduce in WSL:

```bash
cd /home/rk/SentiensHermes/senai-skills
.venv/bin/python -m unittest tests.skills.test_registry -v
.venv/bin/python -m unittest discover -s tests -v
```

Expected: nine feature tests pass; existing wrapper tests remain green. Tests use temporary fixtures and fake execution callbacks, with no model/network/bot/schedule activity. Restart persistence, context reuse, duplicate rejection and inert scripts are verified offline.

Live Codex/manual user demonstration: NOT RUN. Public-repository/archive ingestion, revision history, failed candidates and rollback: NOT IMPLEMENTED; no acceptance claim.

Full offline regression: PASS, 135 tests (126 baseline plus 9 registry tests), run 2026-11-09. No live execution claimed.

## Outcome step

Run `.venv/bin/python -m unittest discover -s tests/skills -v`: expected 15 passing tests. New tests first failed on missing Check export, then passed. Test fixtures use temporary registries and caller-observed fake checks. No live model or automatic learner has been tested.

Outcome-step complete offline suite: PASS, 151 tests. Scope guard: PASS. Retained log: outputs/skills-qa/outcomes-suite.log. No live checks performed.

## Revision proposal step

`.venv/bin/python -m unittest tests.skills.test_revisions -v`: eight passing tests after first failing on missing Registry.propose_revision. `.venv/bin/python -m unittest discover -s tests/skills -v`: 23 passing tests. Uses temporary registries only. Verifies active skill unchanged before/after proposal and restart, supporting file preservation and atomic invalid-input rejection. Candidate hash tampering fails closed. Live reviewer/model and candidate activation NOT RUN/NOT IMPLEMENTED.

Revision-step full offline suite: PASS, 159 tests. Ownership guard: PASS. Log retained at outputs/skills-qa/revisions-suite.log. No live checks performed.

## Regression validation step

Run `.venv/bin/python -m unittest tests.skills.test_validation -v`: expected eight passing tests. First red run is retained in outputs/skills-qa/validation-red.log. Feature suite currently passes 31 tests. Fixtures and checking callbacks are offline; no live model, automatic learning trigger or production state used. Every pass leaves the active skill unchanged. Activation/rollback remain pending.

Validation-step complete offline suite: PASS, 167 tests. Scope guard: PASS. Retained log: outputs/skills-qa/validation-suite.log. No live checks performed.

## Activation and rollback step

Run `.venv/bin/python -m unittest tests.skills.test_activation -v`: expected eleven passing tests. Red failure log: outputs/skills-qa/activation-red.log. Feature suite now passes 42 tests. Fixtures/check callbacks are offline and temporary. Checks prove active selection switches only after latest pass, persists after restart, and rollback restores prior bytes while retaining audit/evidence. Live Codex execution and normal CLI/production integration NOT RUN.

Activation-step full offline suite: PASS, 178 tests. Ownership guard: PASS. Log retained at outputs/skills-qa/activation-suite.log. No live/production checks performed.

## Feature-local CLI manual commands

From the assigned WSL worktree:

```bash
.venv/bin/python -m senai.skills --help
.venv/bin/python -m senai.skills list
.venv/bin/python -m senai.skills demo
```

Expected: help lists commands; an empty main registry lists []; demo returns mode offline-simulated, activated_version 2, restored_version 1 and actions import/activate/rollback. Demo prints its isolated project path. Inspect the retained fixture with:

```bash
.venv/bin/python -m senai.skills --project PRINTED_DEMO_PROJECT list
.venv/bin/python -m senai.skills --project PRINTED_DEMO_PROJECT show demo-workflow
.venv/bin/python -m senai.skills --project PRINTED_DEMO_PROJECT history demo-workflow
```

To acquire a real local skill package, explicitly choose its source directory:

```bash
.venv/bin/python -m senai.skills import /absolute/path/to/skill-package
.venv/bin/python -m senai.skills list
.venv/bin/python -m senai.skills show IMPORTED_NAME
.venv/bin/python -m senai.skills context IMPORTED_NAME "Your request"
```

The import persists in outputs/skills/; subsequent calls list it. Unknown/duplicate/malformed inputs return 2. context only exports instructions and request; no model runs. There are no bundled permanent real skills in this feature. Strict metadata compatibility still applies.

Observed offline CLI QA PASS: executed real module demo, then a separate CLI process listed saved demo-workflow v1. JSON logs: outputs/skills-qa/cli-demo-report.json and cli-demo-list.json. Eight CLI behavior tests pass; red log outputs/skills-qa/cli-red.log. No live model or production usage tested.

CLI-step full offline suite: PASS, 186 tests (50 skills tests). Scope guard: PASS. Retained full log: outputs/skills-qa/cli-suite.log.

## Reviewer adapter step

```bash
.venv/bin/python -m unittest tests.skills.test_review -v
.venv/bin/python -m unittest tests.skills.test_cli -v
.venv/bin/python -m senai.skills review --help
```

Expected: twelve reviewer tests and ten CLI tests pass. Tests use injected model replies and a real wrapper subprocess with a temporary fake codex executable; they are not live model tests. Initial red log: outputs/skills-qa/review-red.log. Installed-option inspection PASS: outputs/skills-qa/review-parser-check.txt. Required flags: --output-schema, --sandbox, --skip-git-repo-check, --output-last-message.

For an explicitly desired live review, first inspect saved outcomes for the selected project, then choose observed-check IDs for the current version:

```bash
.venv/bin/python -m senai.skills --project YOUR_PROJECT outcomes SKILL_NAME
.venv/bin/python -m senai.skills --project YOUR_PROJECT review SKILL_NAME --outcome OUTCOME_ID
.venv/bin/python -m senai.skills --project YOUR_PROJECT revisions SKILL_NAME
```

The review command uses installed Codex/auth and may consume model usage. Expected: no_change or an inactive proposal. Existing active skill remains unchanged; proposed revision has zero validation attempts. A proposal must be independently regression-checked before activation. Review of synthetic demo evidence is only a transport test, not proof of genuine improvement. No live reviewer or real model reuse has been run in this step.

Reviewer-step full offline suite: PASS, 200 tests (64 skills tests). Ownership guard: PASS. Retained log outputs/skills-qa/review-suite.log. No live model/production checks performed.

## Metadata compatibility step

```bash
.venv/bin/python -m pip install --only-binary=:all: -r requirements-skills.txt
.venv/bin/python -m unittest tests.skills.test_metadata -v
.venv/bin/python -m senai.skills metadata SKILL_NAME
```

Expected: eight metadata tests pass; metadata command prints validated optional declarations for an already imported skill. Missing names return 2. Pin is PyYAML==6.0.3; no global install is needed. CLI metadata behavior is covered offline as well.

Tests verify folded descriptions/comments, optional standard fields, nested Hermes metadata/version, rejected tags/aliases/anchors/duplicates/merge keys, limits, blocked incompatible execution and preservation through model-reply fixture -> proposal -> validation -> activation. They do not prove real instruction safety/runtime compatibility. Initial red log: outputs/skills-qa/metadata-red.log; targeted integration log: metadata-integration.log. Public repository/network and live-model QA not performed in this milestone.

Metadata-step full offline suite: PASS, 209 tests (73 skills tests). Scope guard: PASS. Log outputs/skills-qa/metadata-suite.log. No live/network skill acquisition tested.

## Obsidian planning status

NOT IMPLEMENTED/NOT RUN: export command and Obsidian UI check. Planned acceptance is to open generated outputs/skills-vault/ as an existing vault, inspect skill origin/history, refresh after accepted revision/rollback and verify personal notes preserved. Full plan in workplan.md. No personal vault has been accessed.
