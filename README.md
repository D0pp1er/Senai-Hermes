# senai

A small Codex CLI wrapper for writing and editing code. Requires Python 3.10+
and an installed, signed-in Codex CLI (`codex login`). No runtime Python dependencies.

## Install in WSL

```bash
cd /home/rk/SentiensHermes/senai
python3 -m pip install --user --no-build-isolation -e .
export PATH="$HOME/.local/bin:$PATH"
senai --help
```

The editable install uses this checkout, so code changes apply immediately.
The PATH export is only needed if ~/.local/bin is missing from your shell PATH.
On distributions that disallow user pip installations, install into a virtual
environment with `python3 -m venv .venv`, activate it with
`source .venv/bin/activate`, and run `python3 -m pip install -e .`.

## Run

```bash
senai "Create hello.py that prints Hello"
senai "Edit hello.py to print Hello world"
senai --project /path/to/repo "Create a function that adds two numbers"
```

All generated code goes into `<project>/outputs/` (current directory by default).
The wrapper creates this folder and uses it as the Codex workspace. Existing
code must be inside outputs/ to be edited. Paths in requests are relative to
outputs/: ask for `hello.py`, not `outputs/hello.py`.
The parent project normally must be a trusted Git repository (`git init` first).
For a folder without Git, explicitly pass `--skip-git-repo-check`.
Temporary response files also stay inside outputs/ and are removed after each
invocation. The final response is printed to your terminal.

Write/edit exit codes: 0 success, 2 input/execution failure, 130 interrupted.
Chat/native/review modes preserve Codex exit codes; wrapper validation errors return 2.

## Verify

```bash
python3 -m unittest discover -s tests -v
senai --help
git log --oneline
```

Tests mock Codex to verify transport without consuming account usage.
For a live check, run the two hello.py examples and inspect outputs/hello.py.
Check generated code independently.

## Design and limits

- A modular Python package with a `senai` console entry point and no runtime dependencies.
- Write/edit mode handles one request per invocation; chat and resume use native
  Codex sessions. No custom semantic memory or scheduler; an authorized Telegram text adapter is available.
- Uses existing Codex authentication and configuration; no separate API key.
- Write/edit mode runs `codex exec --sandbox workspace-write` in outputs/,
  with the request on stdin. JSON mode streams native events; other modes delegate native workflows.
- Output scope is enforced by the selected workspace and explicit instructions;
  this is not an independent filesystem jail. Codex configuration, tools, and
  inherited project instructions still apply.
- Write/edit mode normally buffers progress and prints the final response; --json streams events. Native/chat/review
  modes preserve terminal streams and native arguments. Failures may leave partial edits.
- Development uses unittest with small red/green/refactor steps; see CHANGELOG.md.
- Reference: https://learn.chatgpt.com/docs/cli/reference

## Project layout

```text
senai/                 Python package
  cli.py               Command parsing and request orchestration
  prompts.py           Write/edit instructions
  codex.py             Codex subprocess adapter
  workspace.py         Output-directory validation
  options.py           Explicit execution/configuration options
  exec_flags.py        Native exec flag parsing/forwarding
  native.py            Interactive, review, and native command adapters
  __main__.py          python3 -m senai support
tests/                 unittest tests grouped by responsibility
projectprogress/       Objectives, achievements, and current task
outputs/               Generated code (ignored by Git)
pyproject.toml         Package metadata and console entry point
```

Keep command handling in cli.py, reusable instructions in prompts.py, and Codex
process details in codex.py. Add corresponding tests under tests/. Update
projectprogress/ and CHANGELOG.md when completing a change. Reinstall the editable
package after changing packaging metadata or entry points.

## Codex configuration

```bash
senai --model YOUR_MODEL --profile YOUR_PROFILE -c model_reasoning_effort=medium "Write code"
```

Model/profile availability is determined by your Codex installation and account.

## Image context

```bash
senai -i /path/to/design.png -i /path/to/detail.png "Build this design"
```

Image paths are relative to your calling directory. Files are read as context; generated code stays in outputs/.

## Web search

```bash
senai --search "Use current official documentation to implement this API"
```

This enables native Codex live search through its configuration.

## Installed skills

```bash
senai --skill YOUR_INSTALLED_SKILL "Write code using this workflow"
```

Repeat --skill to select more than one. This emits native `$name` mentions without shell expansion. Codex resolves installed repository/user/plugin skills; a missing skill is not installed automatically. Repository skills use native `.agents/skills` discovery.
Reference: https://learn.chatgpt.com/docs/build-skills

## Continue a session

```bash
senai --last "Continue the implementation"
senai --resume SESSION_ID "Fix the previous issue"
```

Use sessions originally created in this project outputs/ workspace. --last uses native cwd filtering. Session history remains in the normal Codex state location; this is native conversation continuity, not automatic semantic memory.

## Interactive Codex

```bash
senai chat
senai chat --project /path/to/repo
```

This opens native Codex in outputs/. Use its `/skills`, `/model`, `/permissions`, and other commands as supported by your installed version. It requires an interactive terminal; input/output and approval prompts are not buffered. Exit normally with the native UI.

## Native command compatibility

```bash
senai codex -- --version
senai codex -- exec --help
senai codex -- exec --json "Write a small function"
senai codex -- mcp list
senai codex -- plugin --help
senai codex -- resume --last
senai codex --project /path/to/repo -- review --uncommitted
```

The wrapper forwards arguments after `--` to installed Codex unchanged, with
outputs/ as cwd and workspace-write as the default sandbox. This preserves native
MCP/plugins, review, configuration, JSON event streams, sessions, and other
installed commands without rebuilding their implementations. Native image/input
paths are relative to outputs/, unlike the convenience -i option.

Explicit --cd/-C, --add-dir, --worktree, and --remote are rejected because they
conflict with the local outputs/ policy. Known output-path flags must stay inside
outputs/. Other options are interpreted by Codex; an unsupported flag produces
its native error/exit code. Global Codex account/config/session state stays in its
usual user directories. This is an execution adapter, not a separate filesystem
jail; configured tools can have effects outside the code workspace.

Wrapper keywords `chat`, `review`, `telegram`, and `codex` are reserved only as the first argument. To
use those words as a literal write/edit request, put `--` before the request.

## Code review

```bash
senai review
senai review --base main
senai review --commit COMMIT_SHA
```

This invokes native Codex review in read-only mode. Review uses Git repository
scope (which can include files in the parent repository), not just outputs/.
Review findings stream to the terminal. The default is --uncommitted.

The installed-command tests use a deterministic fake Codex child process, so the suite stays offline. They are skipped only when senai is not installed. Live model checks are recorded separately in CHANGELOG.md.

## Verified compatibility baseline

Tested with WSL Ubuntu-22.04, Python 3.10, and Codex CLI 0.167.0.
- 126 offline tests pass, including installed-command child-process tests.
- Installed CLI checks: version, exec/resume/review/MCP/plugin help, feature listing.
- Live checks: search-enabled code creation, session resume retaining a marker,
  interactive launch, installed skill picker, and clean /quit exit.
- Model/profile/image transport is tested; each model, skill, MCP server, plugin,
  and platform-specific command still requires its own configured environment.
- Native argument forwarding covers commands not represented by convenience flags.
  Relocating execution outside outputs/ is intentionally unsupported.

See main task.md for the complete PDF requirements and remaining deliverables.

## Guides

- [New-user features guide](projectprogress/features.md)
- [Manual QA checklist](tests/manualqa.md)
- [Architecture and execution flow](projectprogress/architecture.md)

When execution behavior changes, update architecture.md together with relevant tests, user examples, and progress records.

## Codex exec options on ordinary requests

```bash
senai "Create a C++ Hello World program" --skip-git-repo-check
senai "Describe this workspace without edits" --skip-git-repo-check --json -o response.txt
printf '%s\n' 'Create hello.py' | senai --skip-git-repo-check
senai -C /path/to/project "Describe the code without edits" -s read-only
senai --version
```

The convenience parser recognizes every option name in installed Codex 0.167.0
`exec --help`; a regression test detects new unrecognized options. Flags can appear
before or after the quoted request. --cd/-C chooses the parent project, retaining
the outputs/ convention. --worktree/--add-dir remain incompatible with that policy.
Other interactive-only commands/options use `senai chat` or `senai codex -- ...`.

Native --enable/--disable, --strict-config, --oss/--local-provider, --ephemeral,
--ignore-user-config, --ignore-rules, --thread-source, --cyber-access-program,
sandbox/approval options, --color, --output-schema, and response/JSON options are
now available directly. Native authentication, feature availability, and invalid
option combinations remain Codex responsibilities.

--json streams only native event records to stdout; no final text is appended.
-o/--output-last-message retains the final response inside outputs/. The wrapper
uses a unique internal capture first, then saves a successful response, so a stale
file cannot be mistaken for a new result. Input schema/image paths resolve from
the calling directory; generated output paths resolve from outputs/.

## Telegram control

Run the guided setup from this checkout:

```bash
bash scripts/setup_telegram.sh --project /path/to/project --skip-git-repo-check
```

The wizard prompts privately, validates the bot, pairs an account with a local
code, saves mode-600 per-project configuration, and starts the service. No manual
user-ID lookup or environment exports are needed. All paired users share one
persistent Codex session; future turns and restarts resume its exact ID.

See [Telegram setup](projectprogress/telegram.md) for startup, additional pairing,
local revocation, /session, compatibility with old configuration, and limits.
The old bot was user-verified live; new setup/pairing still needs manual acceptance.

## Parallel feature development

See [parallel workstreams](projectprogress/parallel/README.md) for four isolated WSL
worktrees/environments, ownership rules, and the four self-contained chat prompts.
