# Changes

## Repository setup
- Initialized a separate local Git repository in senai/.
- Chose Python's standard library for CLI parsing, process execution, and tests.
- Scope is write/edit code only; no memory, scheduling, or messaging features.

## Request input
- Added a quoted request and --project option, validation, and focused instructions.
- TDD red: unittest failed because senai did not exist.
- TDD green: four input/context tests pass with execution mocked.
- Codex execution remains the next step.

## Codex execution
- Added codex exec with workspace-write, project context, and stdin prompt delivery.
- Capture the final message separately from process diagnostics; propagate failures.
- TDD red: four execution tests failed against the placeholder.
- TDD green: all nine tests pass, including missing CLI and empty output cases.
- Checked options against installed Codex CLI 0.167.0-alpha.3.2 help.
