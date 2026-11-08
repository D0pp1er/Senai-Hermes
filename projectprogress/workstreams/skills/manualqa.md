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
