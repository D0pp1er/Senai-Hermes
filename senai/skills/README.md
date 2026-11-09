# Skills: usage and architecture

## Basic commands

After senai setup, these use the saved project:
~~~bash
senai skill list
senai skill import /path/to/package
senai skill import "Preserve identifier strings and check leading zeros"
senai skill use csv-identifiers
senai "Implement CSV handling using the selected workflow"
senai skill show csv-identifiers
senai skill use none
senai skill export obsidian
~~~

A local source is a folder containing SKILL.md (or the file itself). A plain workflow
prompts for a lowercase-hyphenated name, description and explicit import confirmation;
it creates a local user-authored package, not a claimed learned model capability.
Import validates/copies a package. use explicitly selects an accepted active package
for later ordinary requests in this project. list shows origin and selection.
show prints instructions, package path and the configured Obsidian destination.

First export asks for a dedicated local vault folder; Enter is not a guessed default.
Successful export saves the choice. Noninteractive missing path gives an actionable error.
An explicit override is also supported:
~~~bash
senai skill export obsidian --destination /absolute/SkillsVault
~~~
Windows C:/Users/... paths are supported by the exporter from WSL. Export is a one-way,
explicit snapshot, not sync. It preserves personal notes/settings and refuses to
overwrite edited managed pages. It does not install or launch Obsidian. Refresh by
running export again after import/acceptance/activation/rollback.

## Native selection versus registry selection

Native --skill NAME remains a literal installed-Codex skill mention.
Registry selection uses senai skill use NAME, or --registry-skill NAME for one request.
Repeat --registry-skill for multiple packages. Native and registry skills can be combined.
Explicit per-request registry selection overrides the saved registry list.
Saved selection and Obsidian path are project-local at outputs/.skill-settings.json.
The registry is outputs/skills/; there is no implicit global registry scan.

The normal coding/session/memory executor is retained. Exact selected version/digest,
instructions and supporting resource snapshots are added as bounded reference context.
They do not grant permissions or expand the workspace. Outcomes reference the exact
loaded digest, even if an active package changes afterward. Success prose is not a
check: ordinary requests without independent checks record unverified outcomes.

Telegram and cron use the existing child CLI, so the same project's saved registry
selection is loaded into model-executing requests without replacing pairing/session
policy. There are no Telegram /skill management commands. Bare voice replay does not
invoke Codex or generate a new skill outcome. Changing selections does not erase
old model conversation context; use an authorized fresh session if isolation is needed.

## Explicit advanced lifecycle

The original feature CLI is routed as senai skills (and advanced singular commands):
~~~bash
senai skills --help
senai skills import-github openai/skills --commit 49f948faa9258a0c61caceaf225e179651397431 --path skills/.system/skill-creator
senai skills run skill-creator "Create a package at csv-identifiers/SKILL.md preserving leading zeros" --expect-file csv-identifiers/SKILL.md
senai skills outcomes skill-creator
senai skills learn --run RUN_ID --path csv-identifiers --reason "Retain the authored workflow"
senai skills check-learning CANDIDATE_ID --cases /path/to/cases.json
senai skills accept-learning CANDIDATE_ID
senai skills origin csv-identifiers
senai skills history csv-identifiers
senai skills versions csv-identifiers
senai skills rollback csv-identifiers --digest ACCEPTED_DIGEST --reason "Restore accepted behavior"
~~~

Commands involving models/network require your own access and may incur usage.
Copy IDs/digests from actual reports; placeholders are not executable values.
Cases JSON is a list of {name, request, expected_json}; the host compares results.
File-existence checks establish existence, not semantic correctness.
Stages/proposals stay inactive until explicit acceptance with latest passing checks.

Revision flow: record actual outcome -> review with explicit outcome IDs -> inactive
revision -> independent Registry.validate_revision callback -> explicit activate.
Review CLI is senai skills review NAME --outcome OUTCOME_ID; activation is
senai skills activate REVISION_ID. Revision validation is currently Python API
or the controlled demo, not an interactive validation wizard. Rollback restores an
intact accepted digest and retains history.

For a deterministic isolated synthetic lifecycle demo:
~~~bash
senai skills demo
~~~
The separate --live demo makes real Codex calls. Do not call it an offline check.

Important boundary: advanced skills run retains source-run artifacts/reports under
outputs/skill-runs and is intentionally standalone. Its checked artifacts can feed
learn. Normal senai requests retain selected context and outcomes but do not yet
create those authoring run reports or auto-stage generated packages. There is no
automatic universal learning, background proposal activation or weight training.

## Architecture

Human commands -> scoped registry / project selection settings.
Normal request -> selected active immutable packages -> copied context/resources ->
EXISTING native Codex executor (same options/JSON/native UUID/memory) ->
digest-specific outcomes, unverified unless an app supplies independently observed Checks.

Registry SQLite migrations are additive and separate from jobs/media/memory/cron.
Registry validates hashes, paths, bounded YAML and immutable snapshots. Imported/
learned_here/unknown/demo origins are explicit; wording/filenames do not prove origin.
Revisions, checks, accepted versions and activation/rollback history are durable.
Proposals never activate on model success text. A trusted caller can still fabricate
checks: this local state is not cryptographic proof or an instruction security scanner.

Coordinator source: skill_ui.py (basic UX), skill_context.py (existing-executor hook),
cli.py/defaults.py (dispatch/defaults). Feature source: skills/registry.py plus
run/review/learning/origins/obsidian modules. PyYAML==6.0.3 is consolidated in packaging.

Known limits: pinned public GitHub only (no private/arbitrary URL/archive imports),
bounded YAML subset, context budgets, skill/resource snapshots per request, no automatic
snapshot cleanup, textual redaction rather than general secret detection, no live
Obsidian watcher, no Telegram management UI, no guarantee of broad behavioral improvement.
