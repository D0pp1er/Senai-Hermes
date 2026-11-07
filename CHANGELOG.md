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

## Live verification
- Ran the wrapper against an isolated, ignored .local-demo/ Git repository.
- Real Codex created calculator.py; independently verified add(2, 3) == 5.
- A second invocation edited the function to validate numeric arguments.
- Independently verified integer/float addition and TypeError for either invalid argument.
- Both invocations returned final responses and exited successfully.
- Initial sandboxed execution could not access Codex state; live checks succeeded
  after approved execution outside the outer sandbox. Codex's workspace-write
  option remained enabled.
- Demo files are ignored so generated code is separate from wrapper source.

## Output workspace
- Run Codex inside <project>/outputs/ and keep temporary response files there.
- Validate the request before creating outputs; reject a symlinked output root.
- TDD red: three output routing/instruction/path tests failed.
- TDD green: all eleven tests pass.
- Existing files outside outputs/ are preserved; move code into outputs/ to edit it.

## Package command
- Added pyproject.toml with a setuptools single-module package and senai console entry point.
- Installed senai 0.1.0 as an editable WSL user package, without runtime dependencies.
- Before installation: senai --help failed with command not found.
- After installation: senai --help succeeded from both the checkout and /tmp.
- Replaced Windows examples with WSL install, run, and verification instructions.

## Packaged live check
- Ran installed senai to create outputs/package_demo.py through real Codex.
- Independently verified greeting() returns Hello and no root package_demo.py exists.
- All eleven tests pass; outputs/ is ignored by Git.
- Pre-existing untracked hello.py was left untouched.
