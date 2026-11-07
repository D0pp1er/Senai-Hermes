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

## Modular project layout
- Replaced the single module with a senai/ package: CLI, prompts, Codex adapter,
  workspace validation, and module entry point.
- Moved existing tests into tests/test_cli.py and tests/test_codex.py.
- Updated package discovery to include only senai, excluding tests and progress files.
- Added projectprogress/objectives.md, acheivements.md, and current task.md.
- TDD/refactor check: moved tests first; imports failed before adding the modules.
- Verification: all eleven tests pass; editable reinstall and both command entry points succeed.

## Requirements plan
- Added main task.md with required, optional, process, and submission requirements from the PDF.
- Included verifiable TDD or manual acceptance checks for every task, without copying credentials.
- Began incremental native Codex compatibility work; one capability per commit.

## Model/configuration capability
- Added --model/-m, --profile/-p, and repeatable --config/-c without changing defaults.
- TDD: new option tests failed before implementation; all 14 tests now pass.
- Arguments are passed as a list, preserving spaces and preventing shell interpolation.

## Image capability
- Added repeatable --image/-i, resolved before changing to outputs/.
- Missing attachments fail before invoking Codex or creating an output directory.
- TDD: three image tests failed first; all 17 tests now pass.
- Image decoding and model vision support remain Codex responsibilities.

## Web search capability
- Added --search; uses Codex web_search="live" config because exec has no --search flag.
- Default search behavior remains controlled by existing Codex config.
- TDD: two search tests failed first; all 19 tests now pass.

## Installed-skill capability
- Added repeatable --skill NAME, transmitted as literal $NAME mentions on stdin.
- Validate mention names; do not install or fabricate skills. Codex resolves availability.
- TDD: three skill tests failed first; all 22 tests now pass.
- This selects installed skills, not automatic skill learning from experience.

## Session capability
- Added mutually exclusive --resume SESSION and --last using codex exec resume.
- Preserve stdin prompt delivery, final-message capture, and outputs/ context.
- Reject empty/option-like session identifiers. Native Codex retains session history.
- TDD: five resume tests failed first; all 27 tests now pass.

## Interactive capability
- Added senai chat with native terminal streams and slash-command support.
- Native Codex handles tool use, approvals, /skills, /model, and follow-up interaction.
- Keep outputs/ as cwd and preserve native exit status; report missing CLI clearly.
- TDD: three chat tests failed first; all 30 tests now pass.
- Terminal handoff is unit-tested; interactive UI behavior is a user verification step.

## Native compatibility capability
- Added senai codex -- <native arguments> for installed commands and future flags.
- Native streams, interactive input, environment, and status remain native; no shell parsing.
- Reject explicit workspace relocation and known output-path flags escaping outputs/.
- TDD: five native tests failed first; all 35 tests now pass.
- Native configuration/state still lives in normal Codex locations; not every account/tool/flag combination is live-tested.

## Code review capability
- Added senai review with exclusive uncommitted/base/commit selectors.
- Use the native review engine with a read-only sandbox; preserve streams/status.
- TDD: review routing tests failed first; all 38 tests now pass.
- Known short output-path validation also handles -o=path syntax.

## Installed command integration
- Added offline console-script tests with a real fixture child process.
- Initial non-login WSL PATH omitted ~/.local/bin, causing integration tests to skip; added user-install command discovery.
- Red: child process started in the calling directory. Green: direct execution now sets OS cwd to outputs/ as well as Codex --cd.
- Verified literal prompts/skill mentions, final output, temporary cleanup, native streams, and exit status through the installed command.
- All 40 tests pass with no skips; integration tests use a deterministic fake CLI, not a live model.

## Compatibility baseline verification
- Updated README and progress records to match all implemented modes and their exit behavior.
- All 40 tests pass without skips, including installed-command transport checks.
- Installed CLI parsing/version checks succeeded for exec/resume/review/MCP/plugin help.
- Live --search request created outputs/compatibility_demo.py; independently verified marker() returns senai-compatible.
- Live --last recalled that marker without changing files.
- Interactive senai chat opened in outputs/, /skills displayed the installed catalog, and /quit exited with code 0.
- Experiment note: piping native feature output to head triggered an upstream broken-pipe panic; the feature check was rerun with complete capture.
- No claim of testing every external plugin/account/model; workspace-relocation limitations are documented.

## User guide and manual QA
- Added projectprogress/features.md covering installation, first use, every implemented mode/capability, prerequisites, outputs, and limitations.
- Added tests/manualqa.md with an isolated QA workspace, expected outcomes, error cases, and PASS/FAIL/BLOCKED evidence recording.
- Linked both guides from README.md; no product behavior changed.
- Verification: 41 Bash examples pass syntax checks; local links and installed help commands checked. Live manual cases are not marked as executed.

## Architecture documentation
- Added projectprogress/architecture.md with an execution diagram, source links, write/edit tracing, native modes, options, files/state, errors, limits, and test mapping.
- Linked architecture from README and the new-user guide, and documented when it must be updated.
- Documentation only; no runtime behavior changed.
- Verification: reviewed against current source; local links, code fences, and Bash examples checked.
