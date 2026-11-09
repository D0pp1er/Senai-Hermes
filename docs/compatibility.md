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
classifier, skill import/relearning, Discord or OS-installed service is shipped.
See [manual acceptance](manual-testing.md).
