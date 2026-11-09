# Skills manual QA and project-viewer demonstration

For the whole harness, use the [all-feature guide](all-features-demonstration.md) and [combined checklist](all-features-checklist.csv).

Use this guide with [the fillable CSV](skills-demo-checklist.csv). It covers the skills
workstream and its shared CLI/session integration, not just one successful model reply.
For coding/memory/Telegram/cron outside skills, also use [core manual QA](manual-testing.md).

**272 tests were an automated suite, not 272 distinct product features.** That feature
baseline included 136 skills tests plus inherited core tests. After integration,
622 combined offline tests passed. Manual demonstrations below have their own result:
record Pass, Fail or Not run. Never turn a skipped step into a passing claim.

## What to show in a 10–15 minute presentation

1. Import a readable local workflow, list it and inspect its source/origin.
2. Select it, run a real coding request, inspect the artifact, then show that an
   unchecked outcome is explicitly unverified.
3. Export to Obsidian, show its path and index, then demonstrate explicit refresh.
4. Run the offline lifecycle demo: evidence -> proposal -> validation -> activation ->
   rollback. Label its checks synthetic, not real model improvement.
5. If prepared/authorized, show the controlled live demo report or perform it live.
   Explain failed/no-change outcomes honestly.
6. Show the advanced checked-new-skill pipeline and its explicit acceptance gate,
   using prepared evidence if time/model access is limited.

Viewer evidence should include files, JSON history/checks and active digests, not
only a terminal answer. Live checks require your own model/network accounts and may
consume usage. Obsidian viewing requires your own installed app. This guide does not
start any bot/scheduler automatically.

## A. Prepare a disposable environment

Open a new WSL shell so you can exit without changing your normal terminal settings.
From the cloned repository, with its installed venv:

~~~bash
source .venv/bin/activate
export DEMO="$PWD/outputs/skills-viewer-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEMO"
export SENAI_CONFIG="$DEMO/defaults.json"
unset SENAI_INSTALLATION_ROOT
python - <<'PY'
import os
from senai.defaults import save_defaults
save_defaults({"project": os.environ["DEMO"], "skip_git_repo_check": True})
print("Disposable project:", os.environ["DEMO"])
PY
senai skill --help
senai skill list
~~~

This selects only disposable project defaults for this shell. It does not replace
your usual settings file, Telegram pairing, memory or registry. Do not point DEMO
at production. Copy the printed project path into your result sheet. Use this same
shell through the demonstration. Python commands below refer to DEMO from the environment.

Record environment versions:

~~~bash
python --version
codex --version
python -m pip check
git rev-parse HEAD
~~~

If this particular venv was created without pip, bootstrap pip only into that venv
or use the installation guide; do not install globally merely to make a check pass.
The normal new-user venv installation includes pip.

## B. Import, inspect and select a local skill (offline)

Create a human-readable package:

~~~bash
mkdir -p "$DEMO/source"
cat > "$DEMO/source/SKILL.md" <<'EOF'
---
name: demo-identifiers
description: Preserve identifier strings and leading zeros
version: 1.0
---
Treat identifier values as strings, never numbers.
Preserve leading zeros and input order.
For each task, independently inspect the resulting artifact before claiming correctness.
EOF

senai skill import "$DEMO/source"
senai skill list
senai skill show demo-identifiers
senai skills metadata demo-identifiers
senai skills origin demo-identifiers
senai skill use demo-identifiers
senai skill list
~~~

Expected:
- Import succeeds with a digest. No model/script is run by import.
- Name demo-identifiers, version 1.0 and imported origin appear.
- Instructions match the source. Selection is visibly marked after use.
- Accepted package data is under DEMO/outputs/skills/.
- Human-authored local import is not mislabeled learned_here.

Repeat the import: it should reject the duplicate, retaining the original active
package. Verify with show/origin again. This refusal is an expected negative test.

Alternative friendly workflow-text import:

~~~bash
senai skill import "Review filenames before editing and summarize verification results"
~~~

At the prompts:
- Name: demo-review
- Description: Review edits carefully
- Confirmation: yes

Expected: an explicit local package is imported. Repeat with another name and answer
no: no new active package should appear. Workflow text is user-authored, not an
autonomously learned model update.

Persistence check: run another senai skill list invocation. It reopens the registry;
selection and origin should remain. For another terminal, activate its venv and
set the same SENAI_CONFIG/DEMO values, rather than creating new defaults.

## C. Use the selection in a normal request (LIVE Codex)

~~~bash
senai "Create identifiers.json containing exactly the JSON array of strings 007, 000, 42. Preserve all leading zeros. Do not convert identifiers to numbers."
python - <<'PY'
import json, os
from pathlib import Path
path = Path(os.environ["DEMO"]) / "outputs/identifiers.json"
actual = json.loads(path.read_text())
print("Observed artifact:", actual)
assert actual == ["007", "000", "42"], actual
print("PASS: host parsed exact expected strings")
PY
senai skills outcomes demo-identifiers
~~~

Expected:
- Actual saved file passes the host assertion. If it does not, record failure.
- Outcome identifies the selected digest/version.
- Normal execution without a supplied checker is **unverified**, even if the model
  said it checked everything. The later manual assertion is separate evidence and
  does not retroactively upgrade that outcome automatically.
- Context/resources were copied under outputs/.skill-context/ for the selected request.
- No native global skill installation or proposal activation occurred.

Optional explicit evidence recording against that recorded digest:

~~~bash
python - <<'PY'
import json, os
from pathlib import Path
from senai.skills import Registry, Check
project = Path(os.environ["DEMO"])
registry = Registry(project / "outputs/skills")
observed_run = registry.outcomes("demo-identifiers")[-1]
actual = json.loads((project / "outputs/identifiers.json").read_text())
check = Check("exact identifier strings", actual == ["007", "000", "42"],
              "Host parsed identifiers.json and compared type, values and order")
evidence = registry.record_outcome(
    "demo-identifiers", digest=observed_run.skill_digest,
    request=observed_run.request, result=observed_run.result, checks=(check,))
print(evidence.id, evidence.status)
PY
~~~

This is a real, narrow artifact check. Its result must come from the actual file,
not a hardcoded success flag. It does not prove broad code correctness.

One-request override and native coexistence:

~~~bash
senai --registry-skill demo-review "Describe identifiers.json without changing it"
senai skill list
~~~

Expected: per-request override does not replace the saved demo-identifiers selection.
With an actually installed native skill, optionally test:

~~~text
senai --skill YOUR_INSTALLED_NATIVE_SKILL --registry-skill demo-identifiers "REQUEST"
~~~

Do not invent a native skill name and call its failure a registry defect.
Multiple --registry-skill flags select up to eight distinct packages. Native --skill
continues to emit Codex's installed-skill mention; it is not the registry selector.

To clear the default:

~~~bash
senai skill use none
senai skill list
senai skill use demo-identifiers
~~~

Selection is project-local. It does not erase old model conversation context.

## D. Obsidian export and refresh (offline filesystem; viewing is separate)

First show a fully expanded destination to paste into the prompt:

~~~bash
printf 'Paste this absolute path at the vault prompt: %s\n' "$DEMO/vault"
senai skill export obsidian
~~~

Enter the printed absolute path. Do not type the literal text $DEMO/vault into the
prompt: interactive input is not shell-expanded.

Expected:
- Export succeeds and prints vault/index paths.
- Generated/Index.md and managed skill/history notes exist.
- The successful destination is saved for this project.
- These now display that configured destination:

~~~bash
senai skill list
senai skill show demo-identifiers
senai skill export obsidian
~~~

The second export should not ask for an unset path again.
For a dedicated Windows-local vault, use a real path belonging to you:

~~~text
senai skill export obsidian --destination "C:/Users/YOUR_USER/Documents/SenaiDemoVault"
~~~

The destination is an explicit override, saved only after success. Open that folder
as a vault in Obsidian and show Generated/Index. Report GUI viewing separately from
file-export success. Do not install or launch apps automatically during unrelated QA.

Protection and refresh demonstration, using ONLY the disposable vault:

~~~bash
printf '%s\n' 'My personal note: keep me.' > "$DEMO/vault/Personal.md"
senai skill export obsidian
cat "$DEMO/vault/Personal.md"
~~~

Expected: personal note unchanged. Import another package or activate/rollback a
checked version, then run export again: demonstrate updated origin/history notes.

To demonstrate edited-managed-page protection:

~~~bash
cp "$DEMO/vault/Generated/Index.md" "$DEMO/index-backup.md"
printf '
Manually edited page.
' >> "$DEMO/vault/Generated/Index.md"
senai skill export obsidian
~~~

Expected: refusal to overwrite the edited managed page; do not claim refresh passed.
Restore your exact disposable backup before continuing:

~~~bash
cp "$DEMO/index-backup.md" "$DEMO/vault/Generated/Index.md"
senai skill export obsidian
~~~

Exports are one-way snapshots, not automatic sync/watchers. Changes in Obsidian are
not imported as active registry instructions. App settings/personal notes stay owned
by the user. Never run destructive cleanup against a personal vault to make a test pass.

## E. Full lifecycle with no model calls (SYNTHETIC demonstration)

~~~bash
set -o pipefail
senai skills demo | tee "$DEMO/offline-demo.json"
~~~

Expected JSON:
- mode is offline-simulated.
- A unique demo project and registry are reported under outputs/skills-demo/.
- A deliberate synthetic failure produces an evidence-linked inactive revision.
- Injected synthetic regression checks pass.
- activated_version differs from restored_version.
- Actions include import, activate and rollback.

Use the reported project to inspect retained evidence:

~~~bash
export SYNTHETIC_PROJECT="$(python -c 'import json,os; print(json.load(open(os.environ["DEMO"]+"/offline-demo.json"))["project"])')"
senai skills --project "$SYNTHETIC_PROJECT" revisions demo-workflow
senai skills --project "$SYNTHETIC_PROJECT" outcomes demo-workflow
senai skills --project "$SYNTHETIC_PROJECT" history demo-workflow
senai skills --project "$SYNTHETIC_PROJECT" versions demo-workflow
~~~

Explain to the viewer: this proves lifecycle/storage/gates, not actual model learning
or broad performance improvement. Proposals and accepted history are different things.

## F. Controlled actual-model correction/reuse/rollback (OPTIONAL LIVE)

~~~bash
senai skills demo --live | tee "$DEMO/live-demo.json"
~~~

This can make up to four real Codex calls. It uses a deliberately lossy CSV fixture
in a unique project and independently compares real JSON outputs. It is not production.

Success requires report status completed, actual failed baseline checks, passed
candidate validation, passed held-out reuse, and a recorded restored version.
Inspect the reported report_path and artifact/check files. Baseline-already-passed,
no-change, validation-failed or model-error are valid possible outcomes; they are
NOT proof of a completed improvement demo. Save the actual result rather than editing it.

The original feature handoff documented previous successful live runs. This guide's
creation did not rerun them; your demo is separate evidence. Review quality and
generalization beyond the controlled cases remain unverified.

## G. Author and accept a NEW learned package (OPTIONAL LIVE)

This pipeline is intentionally explicit and standalone. It requires a run report
created by senai skills run, not just a normal senai request's response.

~~~bash
senai skills run demo-identifiers "Create learned-identifiers/SKILL.md as a concise reusable skill named learned-identifiers, version 1.0, with a description. Preserve CSV identifier strings, leading zeros and order. When asked for JSON only, return the JSON array without fences." --expect-file learned-identifiers/SKILL.md | tee "$DEMO/author-run.json"
~~~

Check status completed, reported workspace and the actual generated SKILL.md.
--expect-file verifies existence only; it does not prove skill behavior or semantics.

~~~bash
export RUN_ID="$(python -c 'import json,os; print(json.load(open(os.environ["DEMO"]+"/author-run.json"))["id"])')"
senai skills learn --run "$RUN_ID" --path learned-identifiers --reason "Retain the authored identifier workflow after independent checks" | tee "$DEMO/candidate.json"
senai skills learning
senai skill list
~~~

Expected: a proposed candidate appears, but learned-identifiers is NOT active yet.
Copy the actual candidate ID:

~~~bash
export CANDIDATE_ID="$(python -c 'import json,os; print(json.load(open(os.environ["DEMO"]+"/candidate.json"))["id"])')"
senai skills accept-learning "$CANDIDATE_ID"
~~~

Expected negative test: acceptance before passing validation is refused.

Create independent cases:

~~~bash
cat > "$DEMO/cases.json" <<'EOF'
[
  {"name":"leading zeros","request":"Return JSON only: the identifier strings in this CSV row, unchanged: 001,002","expected_json":["001","002"]},
  {"name":"held identifiers","request":"Return JSON only: the identifier strings in this CSV row, unchanged: 007,000,42","expected_json":["007","000","42"]}
]
EOF
senai skills check-learning "$CANDIDATE_ID" --cases "$DEMO/cases.json"
senai skills learning-checks "$CANDIDATE_ID"
~~~

Expected: actual model outputs are compared by the host, and each check's evidence
is retained. If the latest result fails/errors, do not activate or relabel it.

Only after latest checks pass:

~~~bash
senai skills accept-learning "$CANDIDATE_ID"
senai skills origin learned-identifiers
senai skill list
senai skill use learned-identifiers
senai skills run learned-identifiers "Return JSON only: unchanged strings 0007,010,42"
senai skill export obsidian
~~~

Expected: learned_here origin links source run and checks; independently inspect the
held-out result. New origin means checked local package acceptance, not weight training.
The saved vault should refresh only when export is invoked.

Duplicate accepted names are rejected. Use revisions for modifying an existing skill,
not repeated new-package acceptance with the same name.

## H. Revise an existing skill and roll back

Inspect actual outcome IDs:

~~~bash
senai skills outcomes demo-identifiers
~~~

Then use a real ID in this command template (do not type OUTCOME_ID literally):

~~~text
senai skills review demo-identifiers --outcome OUTCOME_ID
senai skills revisions demo-identifiers
~~~

Review makes a live read-only Codex call and returns an inactive proposal or no_change.
No_change is not an activated revision. Copy the actual revision ID if one was proposed.

Independent revision validation is currently the Python API, not a fabricated
senai skills validate command:

~~~python
validation = registry.validate_revision(
    revision_id,
    validator=lambda base, candidate, outcomes: independently_observed_checks)
~~~

Here independently_observed_checks must be Check records produced by actual artifact/
regression evaluation of that candidate. Never write Check(..., True, ...) merely to
unlock activation. The controlled live demo in section F provides a complete working
example, and source senai/skills/live_demo.py shows its actual output comparisons.

After real latest passing validation, these are exact CLI templates:

~~~text
senai skills validations REVISION_ID
senai skills activate REVISION_ID
senai skills versions demo-identifiers
senai skills history demo-identifiers
senai skills rollback demo-identifiers --digest PRIOR_ACCEPTED_DIGEST --reason "Restore previous accepted workflow"
senai skill export obsidian
~~~

Compare active digest/version before and after. Rollback should restore the accepted
package and append history, not erase evidence. Proposed/unaccepted digests must not
be usable as arbitrary rollback destinations.

## I. Optional public package acquisition (NETWORK, no model required)

~~~bash
senai skills import-github openai/skills --commit 49f948faa9258a0c61caceaf225e179651397431 --path skills/.system/skill-creator
senai skills origin skill-creator
senai skills metadata skill-creator
~~~

Expected: exact full commit/path/source and validated content digest. Public GitHub
rate limits/network availability may prevent this step. Private repos/arbitrary URLs/
unpinned latest imports are not supported. Import does not execute bundled scripts.
Source/path/hash validation is not a security scanner or permission grant.

## J. Telegram, cron and native-session integration (OPTIONAL LIVE)

Use a dedicated disposable bot/project, not your normal live bot. The selected
registry belongs to the bot's exact configured project. In that project's CLI,
senai skill use NAME sets its selection. Send an ordinary authorized bot coding
request, inspect the artifact and that project's skills outcomes, and compare
/session before/after. Expected: same native session and pairing, exact skill digest.

There are NO Telegram /skill list/import management commands. Management is local CLI.
The same child pipeline supplies selected project skills to scheduled model requests.
Scheduled voice/photos are not added by this skills integration. Bare /voice replay
does not call Codex, so it should not create a new skill outcome.

For native CLI resume, capture thread.started from senai --json, then use that exact
--resume UUID. Selection must not silently replace it with a different conversation.
Old conversation context remains; clearing selected skills is not a history wipe.

Perform actual scheduled delivery only when you explicitly intend to activate that
disposable schedule. Management commands alone start no worker. Use offline tests
for forced crashes, uncertain sends and destructive fault injection.

## K. Safe rejection and integrity demonstrations

Use only disposable files/registries:
- Duplicate a valid import: original active digest remains unchanged.
- Import malformed YAML/missing SKILL.md: no partial active package.
- Try no-check candidate acceptance: refused.
- Inspect a failed latest validation: activation must refuse.
- Select an unknown/incompatible saved name: clear error, no model call.
- Use a second empty project: first project's selection is not silently loaded.
- Use a non-TTY export with no destination: clear error, no hanging prompt.
- Edit a managed exported page: overwrite refusal, personal notes preserved.

For bounded YAML alias/tag/path/symlink/tamper/corrupt-download/legacy DB migration/
concurrent activation and ownership edge cases, show the deterministic offline suite
rather than damaging real artifacts:

~~~bash
python scripts/test.py
python scripts/test.py discover -s tests/skills -v
python scripts/test.py tests.coordination.test_skills_composition -v
~~~

Current recorded counts: 622 combined, 136 skills-owned, 9 coordinator skills tests.
Counts can change with future commits; record actual output and commit. Tests use
fixtures, not your live credentials. Passing them does not establish account support.

## L. Evidence and viewer scorecard

Fill docs/skills-demo-checklist.csv, or copy it under DEMO to record results.
For each row record:
- actual command/action and project/registry;
- Pass / Fail / Not run;
- actual artifact/report/check/history path;
- whether it was offline synthetic, network acquisition, real Codex, or Obsidian UI;
- why a failure/skip occurred.

Recommended report artifacts under DEMO:
offline-demo.json, live-demo.json (if run), author-run.json, candidate.json,
cases.json, exported vault notes, and a sanitized screenshot/text of actual outputs.
Never include tokens, passwords, personal notes or production transcripts.

Suggested final presentation statement:
'We demonstrated explicit package selection, bounded context and auditable outcomes.
Unchecked model prose stays unverified. Independent declared checks gate acceptance;
rollback retains accepted history. Obsidian is an explicit one-way view. These cases
do not establish universal autonomous learning or exactly-once external execution.'

End by stopping any disposable test service you explicitly started. Do not delete
state while a process is running. Exit the dedicated demo shell to restore the parent
terminal environment. Keep sanitized reports for review; no production state should
have been copied into this demo.
