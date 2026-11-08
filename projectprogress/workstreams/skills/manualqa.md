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
