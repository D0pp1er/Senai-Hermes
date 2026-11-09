# Compatibility

| Area | Verified support / limitation |
| --- | --- |
| Full harness | WSL2 Ubuntu 22.04; POSIX fcntl, ownership, signals and process groups required |
| Python | Package >=3.10; tested Python 3.10 |
| Other Linux/macOS | Not established by this audit |
| Native Windows | Full harness unsupported; use WSL |
| Codex | Last locally checked 0.167.0; exec option regression test detects parser drift |
| Authentication | Native Codex login/API settings retained; dedicated voice key excluded from children |
| Packaging | Isolated venv, editable pip install; dependencies declared in pyproject.toml |
| Optional providers | Telegram, speech, image generation, search, MCP/plugins and model availability require user configuration |
| Persistence | Project-local jobs/media/cron; explicitly installation-global semantic memory |
| Services | No auto-start on import/install |

Convenience flags target the checked Codex baseline, not every future version.
Provider/account limitations are independent of passing transport tests.

The pre-audit integrated baseline has 370 passing offline tests. Earlier live
photo/voice observations are historical, not guarantees for new users. Live
supervised scheduled delivery still needs separately authorized acceptance.

No automatic old-session memory adoption, snapshot refresh, autonomous milestone
classifier, automatic skill activation, Discord or OS-installed service is shipped.
See [manual acceptance](manual-testing.md).

## Fresh-checkout audit

Source 7a8a8e2 was cloned locally into an isolated checkout and installed into a
new virtual environment. Package dependency checks, installed command entry points
and all 370 offline tests passed. The host lacks ensurepip, so QA used venv
--without-pip plus an isolated pip bootstrap; standard new-user setup should install
OS venv support as documented. This is not a test of unauthenticated GitHub access
or a clean OS with every prerequisite installed.

Evidence: outputs/fresh-clone-qa/report.json, install.log and regression.log.
No live bot, native account state, speech call or scheduler was used.
The GitHub clone route can include these changes only after main is pushed.

## Explicit skills integration

Project-scoped skill import, exact context/outcome hooks, checked acceptance, revision/rollback and explicit Obsidian export are now integrated. Native --skill stays independent. PyYAML==6.0.3 is required. Live evidence from the feature handoff is historical; the coordinator rerun uses offline fixtures and isolated configuration. Use python scripts/test.py to avoid loading your own defaults into unit tests.
