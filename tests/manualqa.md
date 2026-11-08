# Manual QA: verify every implemented senai feature

Use an Ubuntu WSL terminal. Run the sections in order and keep the same terminal
open so variables remain defined. These steps create an isolated QA repository
under this project's outputs/; they do not edit the wrapper source.

Record PASS, FAIL, or BLOCKED for each case. BLOCKED means a prerequisite such as
an available model, image, skill, or tool account is missing; do not count it as PASS.
Live senai requests consume Codex usage. Review and interactive screens can vary
by Codex version; judge observable behavior rather than exact prose.

## Setup and offline verification

```bash
cd /home/rk/SentiensHermes/senai
export PATH="$HOME/.local/bin:$PATH"
command -v senai
command -v codex
codex --version
python3 -m unittest discover -s tests -v
senai --help
senai chat --help
senai review --help
senai codex --help
```

Expected: commands resolve to WSL installations; 136 tests pass with no skips when
senai is installed; all help commands exit 0 and show the documented options.
If senai is missing, follow projectprogress/features.md before continuing.

Create a fresh disposable Git repository:

```bash
mkdir -p outputs
QA_ROOT="$(mktemp -d "$PWD/outputs/manualqa.XXXXXX")"
export QA_ROOT
git -C "$QA_ROOT" init -b main
git -C "$QA_ROOT" config user.name "Senai QA"
git -C "$QA_ROOT" config user.email "qa@example.invalid"
printf 'QA repository: %s\n' "$QA_ROOT"
```

All following generated files belong in `$QA_ROOT/outputs/`. The outer QA_ROOT
is itself inside the real project's outputs/. Keep QA_ROOT for inspection.

## QA-01: create code, context, output capture, and output location

```bash
senai --project "$QA_ROOT" "Create qa_math.py containing only def add(a, b) returning a + b. Do not create any other file."
echo $?
cat "$QA_ROOT/outputs/qa_math.py"
python3 - <<'PY'
import os, runpy
from pathlib import Path
root = Path(os.environ['QA_ROOT'])
assert runpy.run_path(str(root / 'outputs/qa_math.py'))['add'](2, 3) == 5
assert not (root / 'qa_math.py').exists()
assert not list((root / 'outputs').glob('.senai-*'))
print('PASS: code, location, and temporary response cleanup')
PY
```

Expected: senai prints a final response and exits 0; the function works; no root-level
qa_math.py exists. The parent-project option must work even though the terminal
remains in the wrapper checkout.

Save a review baseline:

```bash
git -C "$QA_ROOT" add outputs/qa_math.py
git -C "$QA_ROOT" commit -m "Add QA baseline"
git -C "$QA_ROOT" switch -c qa-change
```

## QA-02: edit existing code and independently check behavior

```bash
senai --project "$QA_ROOT" "Edit qa_math.py so add rejects either non-int/non-float argument with TypeError, preserving numeric addition. Only edit this file."
python3 - <<'PY'
import os, runpy
from pathlib import Path
add = runpy.run_path(str(Path(os.environ['QA_ROOT']) / 'outputs/qa_math.py'))['add']
assert add(2, 3) == 5
assert add(1.5, 2) == 3.5
for args in [('2', 3), (2, None)]:
    try:
        add(*args)
    except TypeError:
        continue
    raise AssertionError(f'Expected TypeError for {args}')
print('PASS: editing and validation')
PY
git -C "$QA_ROOT" diff -- outputs/qa_math.py
```

Expected: only the requested file changes; the independent assertions pass.

## QA-03: native project instructions and local tool use

Create instructions only in the QA workspace:

```bash
cat > "$QA_ROOT/outputs/AGENTS.md" <<'EOF'
For this QA workspace, add the comment # SENAI_QA_INSTRUCTIONS to every new Python file.
EOF
senai --project "$QA_ROOT" "Create instruction_check.py defining double(x) as x * 2. Run Python to check double(4) == 8. Only create that file."
grep -n SENAI_QA_INSTRUCTIONS "$QA_ROOT/outputs/instruction_check.py"
```

Expected: the comment exists, the function is correct, and Codex reports its check.
For observable tool events rather than relying on a model's report, also run:

```bash
senai codex --project "$QA_ROOT" -- exec --json "Run python3 to check instruction_check.double(4) == 8. Do not edit files." > "$QA_ROOT/outputs/tool-events.jsonl"
```

Inspect tool-events.jsonl for an actual command-execution event and successful
result. JSON field names may vary by installed Codex version.

## QA-04: model selection

```bash
read -r -p "Enter a model available to your Codex account: " SENAI_MODEL
senai --project "$QA_ROOT" --model "$SENAI_MODEL" "Create model_check.py containing VALUE = 1. Only create that file."
senai codex --project "$QA_ROOT" -- resume --last
```

In resumed Codex, inspect `/status` or `/model` to verify the configured model,
then `/quit`. Expected: available model accepted and file created. Do not use a
model's natural-language claim of its own identity as proof.
Mark BLOCKED if no known model ID is available. The offline test_options suite
separately verifies the wrapper's exact model argument forwarding.

## QA-05: profile and repeated configuration overrides

Use an existing Codex profile, not the literal placeholder below:

```bash
read -r -p "Enter an existing Codex profile name: " SENAI_PROFILE
senai --project "$QA_ROOT" --profile "$SENAI_PROFILE" "Create profile_check.py containing VALUE = 2. Only create that file."
senai --project "$QA_ROOT" -c 'model_reasoning_effort="medium"' -c 'web_search="disabled"' "Create config_check.py containing VALUE = 3. Only create that file."
```

Expected: profile-specific settings apply and both overrides are accepted. Inspect
the resulting session through `senai codex --project "$QA_ROOT" -- resume --last`
and `/status` or available model/config screens; exit with `/quit`.
Use settings supported by your chosen model. Mark the profile case BLOCKED if no
profile exists; an incompatible model setting is an environment limitation.
For exact repeatable-argument verification, run:

```bash
python3 -m unittest tests.test_options -v
```

## QA-06: one image, multiple images, and image-path resolution

```bash
read -r -p "Absolute path of an existing design image: " SENAI_IMAGE
senai --project "$QA_ROOT" --image "$SENAI_IMAGE" "Create design.html matching the attached design. Only create that file."
read -r -p "Absolute path of a second image: " SENAI_IMAGE_2
senai --project "$QA_ROOT" -i "$SENAI_IMAGE" -i "$SENAI_IMAGE_2" "Edit design.html using the first image as the layout and the second as detail reference."
```

Open `$QA_ROOT/outputs/design.html` in a browser and compare with both references.
Expected: existing images attach without path errors and generated code stays in
outputs/. Also try an image path relative to the calling directory; do not resolve
it relative to the QA outputs folder. Mark BLOCKED if images or vision access are missing.

## QA-07: live web search

```bash
senai --project "$QA_ROOT" --search "Use live web search to read current official Python documentation. Create searched_example.py with an example and include the official source URL in a comment. Only create that file."
senai codex --project "$QA_ROOT" -- exec --json -c 'web_search="live"' "Use live web search to find official Python documentation and report its source URL without editing files." > "$QA_ROOT/outputs/search-events.jsonl"
```

Expected: the artifact has an appropriate source and native JSON events show
actual search tool activity. A citation alone does not prove that a search ran.
--search enables the tool; if Codex chooses not to use it, record that observation
and retry a request requiring fresh information. Mark BLOCKED for network/account restrictions.

## QA-08: interactive mode and installed-skill discovery

```bash
senai chat --project "$QA_ROOT"
```

Inside the terminal:

1. Confirm the displayed working directory ends in your QA `outputs/`.
2. Enter `/skills`, choose List skills, and inspect entries.
3. Select a relevant coding skill and note its inserted `$skill-name`; cancel input
   if you are only inspecting it.
4. Inspect `/model`, `/status`, and `/permissions` without changing unrelated settings.
5. Enter `/quit`.

Expected: screens respond, the native skill picker works, and the wrapper returns
to the shell. Use `echo $?` immediately to inspect the exit code; normal /quit is 0.

## QA-09: explicit skill selection (single and repeated)

Use exact installed names from QA-08, without the leading `$`:

```bash
read -r -p "Relevant installed skill name: " SENAI_SKILL
senai --project "$QA_ROOT" --skill "$SENAI_SKILL" "Use the selected skill to make a small code improvement in qa_math.py. Explain which workflow was applied."
read -r -p "Second compatible installed skill name: " SENAI_SKILL_2
senai --project "$QA_ROOT" --skill "$SENAI_SKILL" --skill "$SENAI_SKILL_2" "Use both selected workflows for a focused code improvement."
```

Expected: the skills are found and their documented workflow is reflected in the
work. Inspect the saved native session/transcript for the literal mentions and
skill loading. A response claiming skill use is insufficient by itself.
Mark BLOCKED if suitable installed skills are unavailable. This does not install
skills or test automatic learning, which senai has not implemented.

## QA-10: resume latest conversation

Run these consecutively without starting another session in the QA workspace:

```bash
senai --project "$QA_ROOT" "Do not edit files. Remember this session marker: QA-CONTEXT-731. Reply with that marker."
senai --project "$QA_ROOT" --last "Do not edit files. What exact session marker did I give you in the preceding request?"
```

Expected: the second call returns QA-CONTEXT-731 even though its request does not
contain the marker. This verifies conversation continuity, not custom semantic memory.

## QA-11: resume by session ID or name

```bash
senai codex --project "$QA_ROOT" -- resume --last
```

Use `/status` if it exposes the session ID, or `/quit` and copy the ID from the
native reconnect instruction. Then:

```bash
read -r -p "Session ID from the QA session: " SENAI_SESSION
senai --project "$QA_ROOT" --resume "$SENAI_SESSION" "Do not edit files. Recall the marker from this session."
```

Expected: QA-CONTEXT-731 is retained. Use the ID from the same QA project, not an
unrelated session. A saved native session name may be used in place of the ID.

## QA-12: read-only code review, all three scopes

The main baseline and qa-change branch were created in QA-01. First inspect and
review current uncommitted changes:

```bash
git -C "$QA_ROOT" diff > "$QA_ROOT/outputs/before-review.diff"
senai review --project "$QA_ROOT"
git -C "$QA_ROOT" diff > "$QA_ROOT/outputs/after-review.diff"
cmp "$QA_ROOT/outputs/before-review.diff" "$QA_ROOT/outputs/after-review.diff"
senai review --project "$QA_ROOT" --uncommitted
```

Expected: review findings or an explicit no-findings result; tracked changes stay
identical. Inspect untracked source files too: diff alone does not cover them.
Review streams output and should not edit files.

Create a QA commit, then check branch and commit targets:

```bash
git -C "$QA_ROOT" add outputs/qa_math.py
git -C "$QA_ROOT" commit -m "Validate QA arguments"
senai review --project "$QA_ROOT" --base main
QA_COMMIT="$(git -C "$QA_ROOT" rev-parse HEAD)"
senai review --project "$QA_ROOT" --commit "$QA_COMMIT"
```

Expected: each selector is accepted and reviews the intended Git scope. Model
findings need human judgment; successful execution does not prove every bug was found.

## QA-13: native help, configured tools/plugins, and JSON events

```bash
senai codex -- --version
senai codex -- exec --help
senai codex -- mcp list
senai codex -- plugin --help
senai codex --project "$QA_ROOT" -- exec --json "List the files here without editing them." > "$QA_ROOT/outputs/native-events.jsonl"
senai codex --project "$QA_ROOT" -- exec -o final-response.txt "List the files here without editing them."
cat "$QA_ROOT/outputs/final-response.txt"
```

Expected: native help/version match your installation; MCP list displays configured
servers (an empty list is valid); plugin help displays usage. The event file contains
JSON records, and final-response.txt is inside QA outputs/. For actual external tool
execution, supply a configured tool/account and inspect its real result; otherwise
mark external integration execution BLOCKED, not PASS.

## QA-14: validation and native error/exit propagation

Run each failing command separately and immediately inspect `echo $?`:

```bash
senai --project "$QA_ROOT" " "
echo $?
senai --project "$QA_ROOT/not-a-project" "Write code"
echo $?
senai --project "$QA_ROOT" -i "$QA_ROOT/missing-image.png" "Build this"
echo $?
senai --project "$QA_ROOT" --skill 'invalid skill name' "Write code"
echo $?
senai --project "$QA_ROOT" --resume=-invalid "Continue"
echo $?
senai --project "$QA_ROOT" --resume SOME_SESSION --last "Continue"
echo $?
senai review --project "$QA_ROOT" --base main --commit abc123
echo $?
senai codex --project "$QA_ROOT" -- --senai-qa-unknown-option
echo $?
```

Expected: nonzero status and useful error; wrapper input errors are 2. No model
request should be needed for these validation/parser failures. The unknown native
option must expose Codex's own error and exit status. The offline suite also covers
missing Codex, failed subprocess, missing final response, and process status preservation.

## QA-15: output-root and output-path protections

```bash
QA_LINK_ROOT="$(mktemp -d "$PWD/outputs/manualqa-link.XXXXXX")"
mkdir "$QA_LINK_ROOT/elsewhere"
ln -s "$QA_LINK_ROOT/elsewhere" "$QA_LINK_ROOT/outputs"
senai --project "$QA_LINK_ROOT" "Write code"
echo $?
senai codex --project "$QA_ROOT" -- --cd /tmp
echo $?
senai codex --project "$QA_ROOT" -- exec -o "$QA_ROOT/outside-response.txt" "Write code"
echo $?
test ! -e "$QA_ROOT/outside-response.txt" && echo "PASS: outside response was not created"
```

Expected: each protected invocation fails with 2 before calling Codex. Also try
--add-dir, --worktree, and --remote; they must be rejected for conflicting with outputs/.
This verifies explicit path handling, not an independent sandbox for arbitrary tools.

## QA-16: interruption

Start a harmless longer write request in the disposable QA project. While it is
running, press Ctrl+C once, then inspect `echo $?`.

Expected: ordinary write/edit mode reports interruption and returns 130. Inspect
outputs/ for partial files. Interactive/native modes preserve their own terminal
and exit behavior. Do not interrupt an important real project just to run this case.

## Results record

Copy this table into a QA run note under outputs/ and fill it in. Record the date,
Codex version, Python version, and QA_ROOT. Do not include credentials.

| Case | Feature | PASS / FAIL / BLOCKED | Evidence / observed result |
| --- | --- | --- | --- |
| Setup | Install, command discovery, help, offline suite | | |
| QA-01 | Create/input/context/final response/output location | | |
| QA-02 | Edit code and validate behavior | | |
| QA-03 | Project instructions and local tools | | |
| QA-04 | Model selection | | |
| QA-05 | Profile and repeated config | | |
| QA-06 | Single/repeated image context | | |
| QA-07 | Web search | | |
| QA-08 | Interactive UI and skills picker | | |
| QA-09 | Single/repeated explicit skills | | |
| QA-10 | Resume latest | | |
| QA-11 | Resume by ID/name | | |
| QA-12 | Uncommitted/base/commit review | | |
| QA-13 | Native tools, JSON, final-response file | | |
| QA-14 | Validation and error propagation | | |
| QA-15 | Output workspace/path protections | | |
| QA-16 | Interruption | | |

Leave QA artifacts in outputs/ for review. Starting another run with mktemp creates
a fresh workspace without overwriting your previous run.


## QA-17: reproduce non-Git execution and check Codex option coverage

Use a new directory under the outer SentiensHermes outputs/, outside the wrapper's
Git repository. Keep the original QA_ROOT for the earlier cases.

```bash
mkdir -p /home/rk/SentiensHermes/outputs
QA_NONGIT="$(mktemp -d /home/rk/SentiensHermes/outputs/manualqa-nongit.XXXXXX)"
senai --project "$QA_NONGIT" "Create hello.py that prints Hello"
echo $?
senai --project "$QA_NONGIT" "Create hello.py that prints Hello" --skip-git-repo-check
echo $?
python3 "$QA_NONGIT/outputs/hello.py"
python3 -m unittest tests.test_git_option tests.test_exec_compat -v
```

Expected: first request fails with trusted-directory diagnostics and the supported
flag hint; second succeeds and prints Hello when executed. The tests verify the
reported before/after-request syntax, exact option forwarding, sandbox conflicts,
and coverage against installed Codex exec help without running live model calls.
If your outer directory has since become a trusted Git repo, mark the first-error
reproduction BLOCKED and use a genuinely non-Git project directory instead.

## QA-18: direct JSON events, retained responses, stdin, schema, and version

```bash
senai --project "$QA_ROOT" "Do not edit files. Reply exactly QA_JSON_OK." --json -o qa-response.txt > "$QA_ROOT/outputs/qa-direct-events.jsonl"
python3 - <<'PY'
import json, os
from pathlib import Path
workspace = Path(os.environ['QA_ROOT']) / 'outputs'
events = [json.loads(line) for line in (workspace / 'qa-direct-events.jsonl').read_text().splitlines() if line.strip()]
assert events
assert (workspace / 'qa-response.txt').read_text().strip() == 'QA_JSON_OK'
print('PASS: JSONL output and retained final response')
PY
printf '%s
' 'Do not edit files. Reply exactly QA_STDIN_OK.' | senai --project "$QA_ROOT" --skip-git-repo-check
senai -C "$QA_ROOT" "Do not edit files. Describe the workspace briefly." -s read-only
senai --version
cat > "$QA_ROOT/outputs/qa-schema.json" <<'EOF'
{"type":"object","properties":{"status":{"type":"string"}},"required":["status"],"additionalProperties":false}
EOF
senai --project "$QA_ROOT" "Do not edit files. Return status ok using the supplied schema." --output-schema "$QA_ROOT/outputs/qa-schema.json" -o qa-schema-response.json
python3 - <<'PY'
import json, os
from pathlib import Path
value = json.loads((Path(os.environ['QA_ROOT']) / 'outputs/qa-schema-response.json').read_text())
assert value['status'] == 'ok'
print('PASS: schema response')
PY
```

Expected: JSON stdout consists of parseable records without appended plain final
text; the retained response remains in outputs/. Piped input is handled without a
positional prompt. -C selects the parent project; version requires no prompt.
The schema file is an input, and its final structured response is retained separately.
Add QA-17 and QA-18 to your results table. Approval/bypass option transport is
covered with mocks in test_exec_compat; manual verification does not require disabling protections.


## QA-19: Telegram onboarding and authorized remote execution

Follow [telegram.md](../projectprogress/telegram.md) first. Keep credentials local.
For an isolated live test, select your disposable QA_ROOT instead of the real
project when starting the bot. Allow only your own numeric Telegram user ID.

1. `senai telegram --check`: correct bot identity, no webhook, no code execution.
2. `senai telegram --setup`: send the random phrase privately; terminal prints your
   numeric user ID without executing the phrase or sending a reply.
3. For the legacy route, export the allowlist and start `senai telegram --project "$QA_ROOT"`. For current automated setup, use QA-20 instead.
4. Wait for ready, then send /start in Telegram. Expect usage text.
5. Send `/run Create telegram_hello.py that prints Telegram is working`.
   Expect a request ID, a completion result, and the file under QA_ROOT/outputs/.
6. Run that local Python file independently and compare the printed text.
7. During a longer request, send /status. Expect a prompt running/queued status
   response while code execution continues.
8. Send /result after completion. Expect the saved result, not another code execution.
9. Send /unknown. Expect help, not an executed request.
10. Try a code request from a second, non-allowlisted account and a group chat.
    Expect no reply or generated file. Do not add that account just to force a pass.
11. Request a long response. Expect plain-text split replies with intact Unicode.
12. Stop normally with Ctrl+C. It waits for active work. Restart and verify pending
    results are delivered without rerunning completed work. Messages sent while
    offline are skipped; previously accepted queued jobs remain eligible.
13. Start another poller for the same bot/project. Expect an already-running error.
14. Inspect outputs/.senai-telegram/<bot-id>/ for job logs and durable state; ensure
    no real bot token is in Git. Never publish that state directory.

Add PASS/FAIL/BLOCKED and evidence for each subcase to your results record. The user confirmed live Telegram operation on 2026-11-08; this is not a claim that every subcase above has been individually executed. New installations still need local bot configuration.
Offline coverage is in test_telegram_api.py, test_telegram_jobs.py,
test_telegram_service.py, and test_telegram_integration.py.

No /cancel, attachments, downloads, or remote interactive approvals are implemented;
do not mark those as working features. A failed Telegram send should retain a
pending result and must not cause another Codex execution (covered offline).


## QA-20: automated setup, any-user pairing, and shared persistent memory

Stop the old bot gracefully before this upgrade. Use a disposable project to keep
new acceptance state separate from your real bot state, and only one poller per bot.

```bash
bash scripts/setup_telegram.sh --project "$QA_ROOT"
```

1. Enter the token at the hidden prompt (Enter can reuse a saved/exported token).
2. Send the printed /pair CODE privately to the bot. Expect automatic ID discovery,
   protected env-file saving, and service startup without manual exports.
3. Check the printed config file has mode 600 using `stat -c '%a' PATH`.
   Do not display its contents. It must be outside QA_ROOT/the controlled project.
4. Send `Remember the exact marker SHARED_QA_882. Reply stored.` then `/session`.
   Record the session ID. Ask for the previous marker without including it again.
5. Stop/restart with `senai telegram --project "$QA_ROOT"` from a new terminal,
   without exporting credentials. Ask again; the marker and session ID must persist.
6. In another local terminal run `senai telegram --project "$QA_ROOT" --pair-code`.
   Give that code privately to a second trusted Telegram account. It sends /pair CODE.
7. From that second account ask for the marker and /session. Expect the same shared
   context and ID, intentionally, rather than a separate one-off conversation.
8. Attempt to reuse the consumed code from an unpaired account. Expect pairing failure
   and no execution. A group cannot redeem it. Expiry is ten minutes; offline tests
   cover it using a fake clock if you do not want to wait during live testing.
9. Locally revoke the second ID with `senai telegram --project "$QA_ROOT" --revoke-user ID`.
   Its later prompts must not execute. Existing queued work/pending replies are blocked;
   an already executing request is not automatically cancelled.
10. Try an unsupported/removed session only in a separate test DB, not your real state.
    It must fail visibly and retain its stored ID, never silently create a fresh chat.
11. Check old job history/cursor survives upgrade and new jobs have session_id recorded.
12. Repeat configuration with a saved token and press Enter at the token prompt.
    No secret should appear in terminal output, Git diff, or the child's environment.

Record each result as PASS/FAIL/BLOCKED. Existing v1 bot operation was user-confirmed;
the new onboarding/pairing steps still need this live acceptance. The real Codex
session-resume path has been exercised independently in an isolated QA workspace.
