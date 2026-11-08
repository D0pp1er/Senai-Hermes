# Using senai: a new-user guide

senai is a command-line wrapper around OpenAI Codex CLI. Describe what you want
in plain language; Codex reads context, writes or edits files, and reports the result.
You run it in an Ubuntu WSL terminal, not PowerShell.

## 1. Start here

Prerequisites: Python 3.10+, Git, and Codex CLI installed in WSL. Codex needs a
working login and an account with access. senai uses that existing configuration;
it does not require a separate API key.

For the existing installation:

```bash
cd /home/rk/SentiensHermes/senai
export PATH="$HOME/.local/bin:$PATH"
senai --help
codex --version
```

If `senai` is missing, install this local package:

```bash
python3 -m pip install --user --no-build-isolation -e .
```

If Codex is installed but you have not signed in, run `codex login` and follow
its instructions. If Codex itself is missing, use the official installation guide:
https://learn.chatgpt.com/docs/codex/cli

On systems that prohibit user pip installs, use a virtual environment instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

This checkout is the package source. An editable install uses changes here immediately.
Reinstall after changing package metadata or the console entry point.

## 2. Your first file and edit

From the project directory:

```bash
senai "Create hello.py that prints Hello"
cat outputs/hello.py
senai "Edit hello.py so it prints Hello world"
python3 outputs/hello.py
```

Expected final program output: `Hello world`. The exact Codex response may vary.
The first two senai commands make live model calls and consume Codex usage.
Ordinary write/edit mode prints the final response after the request completes.

## 3. Understand the output folder

- The default project is your current terminal directory.
- Generated code belongs in `<project>/outputs/`; senai creates that folder.
- Requests use paths relative to outputs/: ask for `hello.py`, not `outputs/hello.py`.
- To edit an existing file, put it inside the chosen project's outputs/ directory first.
- Codex normally requires a trusted Git repository. Pass --skip-git-repo-check explicitly for a non-Git folder, or initialize a new project:

```bash
mkdir -p /path/to/my-project
cd /path/to/my-project
git init
senai "Create hello.py that prints Hello"
```

Replace `/path/to/my-project` with a real location. To select a different existing
project without changing your terminal directory:

```bash
senai --project /path/to/my-project "Edit hello.py to print a welcome message"
```

The file is `/path/to/my-project/outputs/hello.py`. Avoid running senai from inside
outputs/ unless you intend to create another nested outputs/ directory.

The wrapper source, tests, and progress records stay in the package repository.
In this repository outputs/ is ignored by Git. Commit source changes deliberately;
generated files are not automatically committed. Temporary response files are
created inside outputs/ and cleaned up. Final responses go to your terminal.

## 4. Choose a mode

| Mode | Command | What happens |
| --- | --- | --- |
| One request | `senai "Write or edit some code"` | Builds instructions, calls Codex, prints the final response. |
| Interactive | `senai chat` | Opens native Codex for back-and-forth work and slash commands. |
| Code review | `senai review` | Streams native review findings in read-only mode. |
| Telegram bot | `senai telegram --project /home/rk/SentiensHermes --skip-git-repo-check` | Process locally paired users in one persistent shared conversation. Requires bot setup. |
| Native compatibility | `senai codex -- <arguments>` | Forwards native commands/flags and preserves their streams and exit code. |

All modes select outputs/ as the working directory. Put wrapper `--project` before
the request, or after `chat`, `review`, or `codex` as shown below. Put native Codex
arguments after the `--` separator in compatibility mode.

## 5. Capabilities and skills

A **capability** is a feature such as image input or session resume. A Codex
**skill** is an installed reusable workflow. senai can request installed skills;
it does not create, install, or improve them automatically.

### Write, edit, inspect, and validate code

```bash
senai "Create math_utils.py with add(a, b), plus a small unittest file"
senai "Edit add() to reject non-numeric arguments and run the relevant tests"
```

Codex can read/search relevant files and use installed development tools while
working. It follows native project instructions such as AGENTS.md. The availability
of compilers, test runners, and external tools depends on the WSL environment.
Inspect the files and test results; a model's claim of success is not independent verification.

### Select a model

```bash
senai --model YOUR_MODEL "Create a small Python function"
```

`-m` is the short form. Replace YOUR_MODEL with an actual model available to your
Codex account. Omitting it preserves your existing Codex model configuration.

### Select a profile or override configuration

```bash
senai --profile YOUR_PROFILE "Write a small Python function"
senai -c 'model_reasoning_effort="medium"' "Write a small Python function"
```

`-p` selects an existing Codex profile. `-c` / `--config` accepts native KEY=VALUE
configuration, can be repeated, and follows Codex TOML parsing. Unsupported profiles,
settings, or model reasoning levels produce native Codex errors. senai does not
create profiles. For multiple overrides, repeat `-c KEY=VALUE` for each setting.

### Attach images

```bash
senai -i /path/to/design.png "Create an HTML page matching this design"
senai -i /path/to/design.png -i /path/to/detail.png "Implement these references"
```

`--image` is the long form. Attachments must be existing files. Convenience-mode
image paths are resolved from the calling terminal directory before entering outputs/.
Image decoding and vision-model support belong to Codex.

### Enable web search

```bash
senai --search "Search current official Python documentation and implement an example"
```

This enables Codex live search through `web_search="live"`. It enables the tool;
whether a particular request uses it depends on Codex. Without --search, the
existing Codex search configuration applies.

### Select installed skills

Find available skills through the interactive UI:

```bash
senai chat
```

Inside Codex, enter `/skills`, choose List skills, and inspect the available
entries. Selecting one inserts its native `$skill-name` mention. Use the exact
inserted skill name (without `$`) with senai:

```bash
senai --skill YOUR_INSTALLED_SKILL "Write code using this workflow"
senai --skill FIRST_SKILL --skill SECOND_SKILL "Use both workflows for this code change"
```

Replace the placeholders with installed, relevant skills. A missing skill is not
installed automatically. Native Codex discovers repository skills under `.agents/skills`
and its configured user/plugin locations. This wrapper sends literal skill mentions
on stdin; the shell does not expand them.

### Resume a conversation

```bash
senai --last "Continue the previous implementation"
senai --resume SESSION_ID "Fix the issue discussed earlier"
```

Use one selector, not both. --last chooses the latest native session for the
outputs/ workspace. SESSION_ID may be a saved session ID or name; get an ID from
native Codex's resume picker or the reconnect information shown on exit.
Use sessions created for the same project/output workspace.

This reuses Codex conversation history. It is not a separate semantic memory
system. Native session/configuration metadata stays in the normal Codex user location.

### Interactive work

```bash
senai chat
senai chat --project /path/to/my-project
```

Type requests directly, steer follow-up work, and use native slash commands such
as `/skills`, `/model`, `/status`, and `/permissions` when supported by your version.
Use `/quit` to leave. Run this mode in a real terminal so input and approval prompts work.

### Review code

```bash
senai review
senai review --base main
senai review --commit COMMIT_SHA
senai review --project /path/to/my-project --uncommitted
```

The default is uncommitted changes, including staged/unstaged/untracked files.
Choose only one of --uncommitted, --base, or --commit. Replace COMMIT_SHA with an
actual commit. Review uses the Git repository's scope, potentially including files
outside outputs/, and runs with a read-only sandbox. Findings stream to the terminal.
A completed review does not guarantee every defect was found.

### Use native commands, tools, plugins, or JSON events

```bash
senai codex -- --version
senai codex -- exec --help
senai codex -- mcp list
senai codex -- plugin --help
senai codex -- exec --json "Create a small example function"
senai codex --project /path/to/my-project -- resume --last
```

Native Codex handles authentication, configured MCP tools, plugins, sessions, and
other installed commands. Listing MCP servers does not configure a new server;
plugin help does not install anything. Use each native command's --help first.
External tools require their normal setup and permissions.

Native arguments remain native: relative image/input/output paths are interpreted
from outputs/. For an image outside it, use an absolute image path. To save a final
response inside outputs/, use a relative output filename:

```bash
senai codex -- exec -o response.txt "Describe the files in this workspace without editing them"
```

This writes `<project>/outputs/response.txt`. Native mode preserves stdin/stdout/stderr
and Codex exit status; JSON mode does not turn events into the convenience-mode final response.

## 6. Limits and troubleshooting

| Symptom | What to check |
| --- | --- |
| `senai: command not found` | Install the package and add ~/.local/bin to PATH, or activate your virtual environment. |
| `Install Codex CLI...` | Install Codex inside WSL and check `command -v codex`. |
| Login/account/model error | Run `codex login` or choose an available model/profile; senai uses native authentication. |
| No immediate response in one-request mode | Progress is buffered until Codex finishes. Interactive/native modes stream output. |
| Missing image / missing project error | Supply an existing file/directory; quote paths containing spaces. |
| Empty final response or failed execution | Read the error, inspect outputs/ for partial changes, and check Codex directly. |
| Unexpected nested outputs/ | Run from the project root or explicitly set --project. |

Workspace-relocation flags --cd/-C, --add-dir, --worktree, and --remote are rejected
in native mode to preserve the local outputs/ policy. Known output-path flags cannot
escape outputs/. This is not an independent filesystem jail: native configuration
and external tools still apply. Avoid granting tools broader access than your task needs.

Write/edit mode returns 0 on success, 2 on validation/execution failure, and 130
on interruption. Native/chat/review modes preserve native exit codes; wrapper errors
return 2. In Bash, `echo $?` immediately after a command shows its exit code.

The first-argument words chat, review, telegram, and codex select modes. For a literal
request with one of those words, use `senai -- "review"`.

## 7. Verify your installation

```bash
cd /home/rk/SentiensHermes/senai
python3 -m unittest discover -s tests -v
senai --help
senai codex -- --version
```

The current suite contains 136 offline tests. Installed-command tests use a fake
Codex child process and skip only if the package is not installed. These tests do
not consume model usage. Live model/tool checks do consume usage and need account access.

For a feature-by-feature manual checklist, read [manualqa.md](../tests/manualqa.md).
For full project requirements and remaining deliverables, read [main task.md](../main%20task.md).

To review how execution works internally, see [architecture.md](architecture.md).

## 8. Native Codex options on a normal request

Options can appear before or after the quoted request. Your non-Git example works as:

```bash
cd /home/rk/SentiensHermes
senai "make a directory named Testbench and create a helloworldcpp to print tumi kemon acho" --skip-git-repo-check
```

Expected file: outputs/Testbench/helloworld.cpp. The Git-check flag is explicit;
senai does not silently disable Codex's normal check for every request.

| Options | Behavior |
| --- | --- |
| --skip-git-repo-check | Allow a request outside a Git repository. |
| -C / --cd | Select the parent project, like --project; generated code still goes into its outputs/. |
| -s / --sandbox | Select the native sandbox (default workspace-write). |
| -a / --ask-for-approval | Pass the native global approval policy before exec. |
| --approve-for-me | Delegate approval review to native Codex; the default sandbox flag is omitted to avoid conflicts. |
| --enable / --disable | Repeatable native feature switches. |
| --strict-config | Ask Codex to reject unrecognized configuration. |
| --oss / --local-provider | Use a locally configured provider; no provider is installed by senai. |
| --ephemeral | Tell Codex not to persist this session. |
| --ignore-user-config / --ignore-rules | Native controls over configuration and rule loading. |
| --thread-source / --cyber-access-program | Native metadata/access options; account access still applies. |
| --color | Native always/never/auto output setting. |
| --output-schema | Existing input schema file; Codex checks/uses its contents. |
| --json | Stream native JSONL events instead of printing a duplicate final response. |
| -o / --output-last-message | Retain a successful final response inside outputs/. |
| -V / --version | Print the installed Codex version without needing a request. |
| --dangerously-bypass-approvals-and-sandbox / --dangerously-bypass-hook-trust | Recognized native options; senai does not enable these by default. |

Examples:

```bash
senai "Describe the files without editing" --skip-git-repo-check --json -o response.txt
senai "Return a result matching this schema" --output-schema /path/to/schema.json
printf '%s\n' 'Create hello.py that prints Hello' | senai --skip-git-repo-check
printf '%s\n' 'Create hello.py that prints Hello' | senai - --skip-git-repo-check
senai --version
```

JSON event records go to stdout as they arrive; stderr carries native diagnostics.
When -o is supplied, outputs/response.txt keeps the final response. The wrapper
copies it from a fresh internal capture only after a successful, nonempty result;
an older saved response is never accepted as proof of a new run.

The parser covers installed Codex 0.167.0 exec option names, with an installed-help
regression check. --worktree and --add-dir are recognized but return a targeted
outputs-policy error. Interactive-only options and subcommands remain available
through native mode as documented above; this is not a promise that every future
Codex flag or every model/feature combination is already supported.

## 9. Telegram control

```bash
bash scripts/setup_telegram.sh --project /path/to/project --skip-git-repo-check
```

The [Telegram guide](telegram.md) explains guided setup: hidden token entry,
validation, private local-code pairing, protected config saving, and automatic
startup. Any operator/account can use it; no personal ID is hardcoded.

All paired accounts share one persistent Codex conversation. /session shows its
saved ID; later messages and restarts resume that exact session. /run, /status,
/result, and /help remain available. Local --pair-code adds accounts and
--revoke-user removes access. Voice, attachments, downloads, and /cancel remain
unimplemented. The new pairing/wizard needs live acceptance; session continuity
has been checked with real Codex.

## Telegram integration merge (2026-11-09)

Telegram uses varied short acknowledgements and asks Codex for concise plain-text replies. Requested code and detail remain available; brevity is a preference, not a hard filter. Existing pairing, configuration and shared session are reused. Discord remains backlog.

## Telegram media

Replies may attach up to four PNG/JPEG images from outputs/. With local speech configuration, /voice QUESTION returns text plus AI-generated audio; bare /voice reads the latest successful answer. Speech uses optional billed API access, configured locally through SENAI_TTS_API_KEY. Live audio acceptance remains pending.

## Installation memory integration (2026-11-09)

Memory is opt-in through one explicit existing installation root:
    export SENAI_INSTALLATION_ROOT=/absolute/path/to/installation
    senai --project /absolute/path/to/project-a "Remember in USER.md: Prefers concise replies"
    senai --project /absolute/path/to/project-b "What response style do I prefer?"

Alternatively pass --installation ROOT on each call. The installation root stays constant across projects; no inference from cwd, home, package location or Telegram identity. One owner per installation only. USER.md and MEMORY.md live at ROOT/outputs/.senai-memory/, alongside human-controlled SOUL.md and memory.db.

Direct management is available as senai memory --installation ROOT remember USER.md "Prefers concise replies" --user-requested. With SENAI_INSTALLATION_ROOT configured, the memory subcommand uses that root automatically.

Fresh execution loads a bounded InstallationMemory snapshot. Native thread.started events bind it in native-snapshots.sqlite3; exact --resume ID reuses that persisted snapshot without rereading changed profiles. --last, ephemeral mode and sessions without a stored snapshot fail clearly rather than silently selecting/rebuilding context. Existing native sessions and old scoped memory are retained and not silently adopted/imported. Unconfigured runs retain the original execution path. Native interactive/pass-through commands do not gain memory injection.

Explicit requests "Remember in USER.md: FACT", "Remember in MEMORY.md: FACT", or "Remember that FACT" are saved after successful execution (the latter defaults to MEMORY.md). Telegram's presentation wrapper is supported when its child inherits the explicitly configured root; no production bot was enabled/restarted for this integration. Automatic SOUL save requests are rejected. App-managed profile instructions are cooperative; this is not a sandbox against hostile filesystem writes.

Trusted app validators can call InstallationRuntime.execute(..., learning=validator). The validator receives (request, successful_response, workspace) and returns LearningDecision objects. A noteworthy event requires noteworthy=True AND verified=True; user_requested must represent real user authorization. Ordinary model output, "Memory:" lines and success text never grant verification or trigger implicit saving. No autonomous noteworthy classifier is introduced. Learning does not refresh an existing session's frozen context.

## Cron integration (2026-11-09)

Merged feature/cron through 46e739d (6a50762); wiring 7e6cf18. Consolidated pinned dependencies, shared senai cron management, opt-in /cron management, existing serialized native-session execution, and currently authorized durable text delivery. All 299 combined tests passed; installed CLI fixture QA and dependency checks passed. Production state/services untouched; live scheduling remains disabled and unverified. See projectprogress/cron.md for usage and limits.

## Supervised cron worker (2026-11-09)

Added explicit senai cron worker / worker-status commands in 58109c0. Execution and delivery loops are independent; scheduled native execution has a configurable process-group deadline. Unknown execution pauses the schedule and bypasses retries; ambiguous sends remain unknown. Singleton locking preserves Telegram's exact shared-session policy. Existing bot --enable-cron mode also drains delivery independently. All 312 tests passed, including disposable offline pipeline/authorized-delivery and restart acceptance. Live acceptance remains pending explicit instruction; production services/state were not used. Startup, shutdown and recovery: projectprogress/cron.md.
