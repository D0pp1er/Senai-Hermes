# Current task

Fix non-Git execution and expose the installed Codex exec options on ordinary senai requests.

Status: complete.

Verification: all 60 tests pass; live C++ and JSON checks pass; documentation links and example syntax pass.

- --skip-git-repo-check works before or after the prompt.
- Parser coverage is checked against installed Codex 0.167.0 exec --help.
- JSON streaming, retained response files, stdin, schema inputs, sandbox/approval,
  feature/provider options, version, and project aliases are implemented.
- All 60 tests pass with no skips.
- The exact reported C++ request succeeded in ~/SentiensHermes; independent compile/run verified its output.
- Live JSON plus saved-response behavior verified separately.
- features.md, architecture.md, ../tests/manualqa.md, and README are updated.

Limits: workspace-relocating flags still conflict with outputs/. Interactive-only
commands/options use native adapters. No automatic Git-check bypass is enabled.
