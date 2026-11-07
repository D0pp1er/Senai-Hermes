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
- The project must be a Git repository for standard Codex execution. For a new project:

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

The first-argument words chat, review, and codex select modes. For a literal
request with one of those words, use `senai -- "review"`.

## 7. Verify your installation

```bash
cd /home/rk/SentiensHermes/senai
python3 -m unittest discover -s tests -v
senai --help
senai codex -- --version
```

The current suite contains 40 offline tests. Installed-command tests use a fake
Codex child process and skip only if the package is not installed. These tests do
not consume model usage. Live model/tool checks do consume usage and need account access.

For a feature-by-feature manual checklist, read [manualqa.md](../tests/manualqa.md).
For full project requirements and remaining deliverables, read [main task.md](../main%20task.md).
