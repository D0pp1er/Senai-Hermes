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

## Working live demo (priority; Obsidian deferred)

```bash
cd /home/rk/SentiensHermes/senai-skills
.venv/bin/python -m senai.skills demo --live
```

Makes up to four authenticated Codex calls; optional --model MODEL. Expected stderr stages 1/6 through 6/6; stdout status completed, baseline_passed false, validation_status passed, reuse_passed true, restored_version 1. It imports a controlled defective fixture into a unique project, not your main registry. No-change/failed/error statuses return 2 and must not be presented as success.

Observed native live run PASS: project outputs/skills-live-demo/run-bv8i5d3a; source report outputs/skills-qa/live-demo-report.json (and that project's outputs/report.json). Actual baseline [[1,2],[10,20]]: only batch-count check passed (1/3 total). Actual regression [["001","002"],["10","20"],["003","9"]]: 4/4 checks. Actual held-out reuse [["007","000","42"]]: 2/2 checks. Activated revision r-86070275eba04b20a9107b6780ee0ffe, then restored v1. Audit import/activate/rollback. No live production state touched.

Inspect retained skill/history from the same checkout:

```bash
.venv/bin/python -m senai.skills --project outputs/skills-live-demo/run-bv8i5d3a show csv-identifiers
.venv/bin/python -m senai.skills --project outputs/skills-live-demo/run-bv8i5d3a revisions csv-identifiers
.venv/bin/python -m senai.skills --project outputs/skills-live-demo/run-bv8i5d3a outcomes csv-identifiers
.venv/bin/python -m senai.skills --project outputs/skills-live-demo/run-bv8i5d3a history csv-identifiers
```

Offline test command `.venv/bin/python -m unittest tests.skills.test_live_demo -v`: six tests use injected executors (not live calls). Red log outputs/skills-qa/live-demo-red.log. Live success above is actual separate verification, not inferred from those tests. Known defective fixture and predetermined checks limit the improvement claim to this example.

Working-demo full offline suite: PASS, 215 tests (79 skills tests). Scope guard: PASS. Full log outputs/skills-qa/live-demo-suite.log. Separate actual live run PASS as detailed above.

## Pinned public GitHub acquisition

Offline verification:

```bash
.venv/bin/python -m unittest tests.skills.test_sources -v
```

Expected: thirteen tests pass. Covers commit/tree/blob identities, restart provenance, bad paths/metadata, symlink ancestors/submodules, truncated trees, corrupt downloads, no partial activation, aggregate/per-file limits, host/credential/redirect restrictions, repository-root packages, CLI routing and preservation of locally revised content. Initial red log outputs/skills-qa/sources-red.log.

Real network CLI acquisition PASS, no model/script execution: source openai/skills at 49f948faa9258a0c61caceaf225e179651397431, path skills/.system/skill-creator. Imported seven files; registry reopened successfully. Package SHA-256 a617b59ca9bc4cf6e15744b6fe4896f1408eac4c1c2d072cc066f720148b59e0. Pin report outputs/skills-qa/github-pin.json; CLI report outputs/skills-qa/github-import-report.json.

Inspect the retained real import:

```bash
.venv/bin/python -m senai.skills --project outputs/skills-import-demo/run-izmdpt0k list
.venv/bin/python -m senai.skills --project outputs/skills-import-demo/run-izmdpt0k show skill-creator
```

For a fresh chosen project (duplicate names are rejected), public import syntax is:

```bash
.venv/bin/python -m senai.skills --project YOUR_PROJECT import-github openai/skills --commit 49f948faa9258a0c61caceaf225e179651397431 --path skills/.system/skill-creator
```

Expected: source URL includes exact commit/path, validation passed and content digest present. This means format/content validation, not instruction safety or production execution. Public GETs are unauthenticated and may fail on rate limits/network availability. Native/global registries remain untouched.

User independently confirmed actual live demo completed in outputs/skills-live-demo/run-k7msx0uu (baseline failure, passing update/reuse, rollback), separate from these acquisition-only checks.

Public-source-step full offline suite: PASS, 228 tests (92 skills tests). Scope guard: PASS. Log outputs/skills-qa/sources-suite.log. Real public acquisition also passed as recorded above.

## Ordinary saved-skill requests

Offline verification:

```bash
.venv/bin/python -m unittest tests.skills.test_run -v
```

Expected: thirteen passing tests. Checks cover context/resource snapshots, unchecked outcomes, passing/failing/errored checkers, model errors, model/native/read-only options, namespace/escape/symlink guards, multiple skills, CLI requests and old-revision identity across concurrent activation. Initial red log outputs/skills-qa/run-red.log; targeted log run-feature.log.

Working user command for retained real public skill:

```bash
.venv/bin/python -m senai.skills --project outputs/skills-import-demo/run-izmdpt0k run skill-creator "Create a concise CSV identifier skill at csv-identifiers/SKILL.md. Preserve identifier strings and leading zeros. Keep all generated files inside this run workspace; no global installation." --expect-file csv-identifiers/SKILL.md
```

Expected: status completed, verification passed for requested file existence, nonempty response, unique workspace/report_path and outcome_ids. Inspect reported workspace to read artifact. Without --expect-file or an injected checker, expected verification is unverified. File checks do not prove semantics; independently validate important task behavior.

Observed native live QA PASS: imported skill-creator generated csv-identifiers/SKILL.md (2,126 bytes) in outputs/skills-import-demo/run-izmdpt0k/outputs/skill-runs/e1da4304dfb841eb84e8b3cf91e30e67/workspace. Explicit file check passed. Host parsed SKILL.md and checked name csv-identifiers separately; PASS. Reports outputs/skills-qa/run-live-report.json and run-live-format-check.json. Outcome ID 46459b96ec5842fe8bbfcc2579b83a3d is linked to the original imported skill-creator digest. No automatic generated-skill registration/native install is claimed. This is actual model evidence, separate from injected offline tests.

Ordinary-run-step full offline suite: PASS, 241 tests (105 skills tests). Scope guard: PASS. Full log outputs/skills-qa/run-suite.log. Separate actual model artifact/format QA PASS as above.

## Checked learned-skill acceptance and origin

```bash
.venv/bin/python -m unittest tests.skills.test_learning -v
```

Expected eleven passing tests: inactive staging/restart, accepted origin/evidence, no/failed/later-error gates, candidate tamper, source-run/path guards, duplicate-name atomicity, imported revision classification, independent JSON checking, legacy origin migration and actual CLI routing/failure codes. Initial red log outputs/skills-qa/learning-red.log. Offline models are injected; native evidence below is separate.

Actual user artifact from run c0f1248ce000468e8303cf4cc1f3fc98 staged with learn --path csv-identifiers into candidate f9f3b4739b2647048767cd79af1926c6. Live check-learning used two requests; expected JSON ["001","002"] and ["007","000","42"] was compared by host, not provided in model prompts. Both passed, then accept-learning succeeded. Reopening registry preserved origin and evidence. Files under outputs/skills-qa/: learn-candidate.json, learn-cases.json, learn-live-checks.json and learn-accepted.json. New package name csv-identifiers, origin learned_here; existing skill-creator remains imported. This is instruction package acquisition/checked reuse, not weight training or broad improvement proof.

Inspect now:

```bash
.venv/bin/python -m senai.skills --project outputs/skills-import-demo/run-izmdpt0k list
.venv/bin/python -m senai.skills --project outputs/skills-import-demo/run-izmdpt0k origin csv-identifiers
.venv/bin/python -m senai.skills --project outputs/skills-import-demo/run-izmdpt0k learning-checks f9f3b4739b2647048767cd79af1926c6
```

For a future generated skill: learn --run RUN_ID --path RELATIVE_PACKAGE --reason TEXT, inspect proposed candidate, provide independent cases to check-learning CANDIDATE_ID --cases FILE, then accept-learning CANDIDATE_ID only if latest checks pass. Staging never activates. Reusing an accepted name requires versioned revisions, not duplicate learning acceptance. Cases JSON is a list of objects with name, request and expected_json. No-check/error/failed cases cannot activate.

Learned-acceptance full offline suite: PASS, 252 tests (116 skills tests). Scope guard: PASS. Log outputs/skills-qa/learning-suite.log. Separate actual candidate checks/acceptance PASS as detailed above.
