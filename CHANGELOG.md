# Changes

## Sequence diagram repair
- Reproduced parse failures in all four diagrams using the pinned Mermaid 11.4.1 parser. Literal semicolons in message/note labels were treated as statement separators.
- Replaced those separators with commas; all four diagrams now pass that parser. QA-only parser/before-source files are under outputs/sequence-qa. No runtime behavior changed.

## GitHub Pages presentation
- Added a self-contained eight-chapter static walkthrough: introduction, install, CLI/chat, CS-student/BJJ/AI profiles, Telegram, guided cron, UFC fixtures skill and Obsidian.
- Added presentation mode, chapter/keyboard controls, command copy buttons, responsive/print CSS and a downloadable human-authored UFC skill. Fixture data is fetched only when the user runs it; no fabricated upcoming schedule.
- Added a presentation-only Pages workflow and explicit publishing/preview instructions. No GitHub settings, push, deployment or production service changed.
- Verified: HTTP page/assets, eight chapters and copy targets/local links, JavaScript syntax and isolated navigation/clipboard behavior; imported the example skill into disposable QA state with no execution. Browser automation failed to initialize, so visual/mobile browser acceptance remains unverified. Runtime code unchanged; full harness suite was not rerun.

## Persistent Senai chat
- Replaced direct native interactive chat with a Senai loop using shared execute_request: workspace/options, selected skills, frozen installation memory, native execution and outcome learning.
- Added private project-local SQLite transcripts, installation-partitioned local sessions, exact native UUID resume, /history all, /sessions, /resume, /new and explicit uncertain-turn fencing. Telegram state/session unchanged.
- TDD: 11 behavior tests failed against old native routing; 16 chat tests now pass, including a real offline Codex child, reopen/frozen snapshots, learning, selected skill outcomes, crash recovery, locks and mapping/symlink integrity. Full isolated regression: 635 passed. Logs: outputs/chat-red.log, chat-green.log, chat-combined-regression.log.
- Added four module sequence diagrams and expanded manual acceptance to 142 cases. Live Codex/Telegram checks were not run; no production state, restart, push or deployment.

## Documentation cleanup
- Removed 12 duplicate/stale navigation, setup, scorecard and aggregate-progress files; replaced historical cron/learning guides with current operational docs. Git retains prior versions.
- Kept one 134-case scorecard, comprehensive feature and skills walkthroughs, detailed module architecture and recovery contracts. Refreshed integrated module guidance and requirement statuses.
- Retained source/tests, contributor policies, workstream delivery records and all runtime/configuration state. Verification is documentation/link/syntax checks only; no bot restart, live schedule or provider call.

## All-feature manual QA
- Added complete onboarding/coding/native session/memory/Telegram/voice/photo/cron/skills/architecture demonstrations and a 134-case fillable checklist.
- Replaced the outdated core-only manual entry point with links to the comprehensive plan; marked live opt-in and offline failure-injection evidence separately.
- Documentation checks only: CSV shape/IDs, shell syntax, embedded Python and local links. No live tasks, bot restarts, schedules or regression rerun.

## Skills manual demonstration guide
- Added a step-by-step viewer guide and 48-case fillable CSV covering selection, outcomes, checked learning, revisions, rollback and Obsidian.
- Marked synthetic, network, live Codex and UI checks separately; manual cases were not executed while writing this documentation.
- Linked from README and core QA; checked CSV structure, shell snippet syntax and local links. No runtime code changed.

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

## Non-Git workspace compatibility
- Reproduced rejection of --skip-git-repo-check in convenience mode.
- Added explicit forwarding of the Codex Git-check option before or after the request.
- TDD: two regression tests failed first; all 42 tests pass. The default Git check remains enabled.

## Codex exec option compatibility
- Added exec_flags.py and an installed-help regression check: every current Codex 0.167.0 exec option name is recognized.
- Added native boolean/value/feature switches, sandbox and approval selection, color, schema input, version, and -C/--cd parent-project aliases.
- Added native JSONL streaming, retained final-response paths, and stdin requests. Fresh internal capture prevents stale retained files from hiding missing responses.
- Recognize workspace-relocation flags with explicit outputs-policy errors instead of generic parser rejection.
- TDD: exec compatibility and output-mode tests failed before implementation; 60 tests now pass with no skips.
- Live verification: the user's exact non-Git command succeeded, and g++ independently compiled outputs/Testbench/helloworld.cpp; it printed tumi kemon acho.
- Live --json plus -o produced parseable native event records and retained SENAI_JSON_OK, with no duplicate plain-text output.
- Updated architecture, features, manual QA, and README to match changed execution behavior.

## Telegram transport
- Created feature/telegram-bot; user selected one-off requests in /home/rk/SentiensHermes.
- Added standard-library Bot API polling, plain-text replies, sanitized errors/rate-limit metadata, local credential loading, and Unicode-safe reply splitting.
- TDD: transport/configuration tests failed before implementation; no live credentials used.

## Telegram job routing
- Added mandatory private-user authorization before execution, help/run/status/result commands, and a bounded queue.
- Added SQLite cursor/job persistence, duplicate update protection, interrupted-job recovery without automatic re-execution, and durable result-delivery progress.
- TDD: routing/store tests failed before implementation; no Telegram network calls are made by these tests.

## Telegram execution service
- Added senai telegram setup/check/polling, a separate single worker, private reply delivery, and a per-bot/project process lock.
- Requests invoke the existing senai module with literal text, non-interactive approvals, and bot-token variables removed from child environments.
- Preserve local stdout/stderr job logs; send split results through a durable outbox without re-running jobs on delivery failures.
- Old Telegram messages are skipped on startup; accepted queued work persists, and previously running work is marked interrupted rather than retried.
- Added real worker-thread responsiveness and setup tests; a failing /result regression exposed and fixed completed results hidden by newer queued jobs.
- No live bot connection has been made; the user is creating a bot with BotFather.

## Telegram integration verification
- Added a full offline authorized-message -> durable queue -> real senai child -> fake Codex -> generated file -> Telegram-result test.
- Verified unauthorized updates never receive a reply or execute, token variables do not reach Codex, and duplicate updates do not rerun work.
- A failing rewound-cursor test exposed a possible polling loop on an already-recorded job; duplicate handling now advances that cursor safely.

## Telegram setup and architecture documentation
- Added projectprogress/telegram.md with BotFather, hidden local token input, ID discovery, startup, commands, state/retry behavior, and explicit v1 limits.
- Updated architecture, feature guide, README, master requirements, and manual QA (QA-19).
- All 100 tests pass offline; no live Telegram connection or bot-controlled model call has been made.
- Documentation verification: local links and 68 Bash examples checked; no live Telegram commands executed.

## Telegram acceptance and merge
- User confirmed live Telegram operation on 2026-11-08 and requested merge into main.
- Updated setup/progress records to distinguish user-confirmed live operation from offline tests and individually unrecorded QA cases.
- Verification: all 100 tests passed before merging; merge commit 46b1b33 integrates the feature into main.

## Persistent Telegram conversation
- Created feature/telegram-sessions. User selected local-code pairing and one shared conversation.
- Capture verified native thread.started IDs and persist the shared session per bot/project. Every subsequent turn resumes that exact ID, never --last or a silent one-off fallback.
- Preserve per-job final responses and JSON events; migrate existing databases without deleting history. Recover a newly created session from interrupted job events.
- Added /session for authorized users. TDD: six session tests failed before implementation.

## Operator-independent Telegram pairing
- Added expiring, single-use local pairing codes; only hashes are stored. Any private account can pair with a code obtained from the operator.
- Persist paired users, support local --pair-code and --revoke-user, and retain legacy allowed-ID compatibility. Explicit revocation overrides legacy configuration.
- Recheck dynamic authorization for queued work and pending delivery. TDD: eight pairing/authorization tests failed before implementation.

## Automated Telegram setup
- Added scripts/setup_telegram.sh and --configure/--start: hidden token entry, API validation, private code pairing, atomic mode-600 token file, and automatic bot startup.
- Saved configuration is discovered per project under XDG_CONFIG_HOME (or ~/.config), outside the controlled workspace; no manual export or numeric ID lookup is needed.
- Added guided setup and file-protection tests. A failing race test exposed code messages being skipped; the backlog is now drained before showing the pairing code.
- Existing --setup, --env-file, and explicit allowed-ID configurations remain supported. No real token was read or changed by these tests.

## Shared-session and setup verification
- Verified two live Codex turns in an isolated QA project: another simulated Telegram user after a runner/store restart recalled the marker through the exact same saved session ID. No bot token was read.
- Added regressions for v1 SQLite migration, configure-and-start using the newly entered token, and expired setup code renewal.
- The new Telegram onboarding itself remains to be verified with the operator bot; tests use fake API clients and private temporary configuration files.

## Shared Telegram setup documentation
- Rewrote the Telegram guide around automated configuration and persistent shared context; updated architecture, feature guide, manual QA-20, requirements, and progress records.
- Documented trusted local pairing, shared-history implications, compatibility, restart behavior, and pending live onboarding acceptance.
- Final documentation check: local links and 69 Bash examples pass. The source branch remains feature/telegram-sessions; no merge or real-token migration was performed.

## Telegram sessions merged
- At user request, merged feature/telegram-sessions into main (664539c) on 2026-11-08.
- All 126 regression tests passed before merge; existing live-token configuration was not read or changed.

## Parallel feature preparation
- Added shared ownership/execution-boundary guidance, repository agent instructions, pinned packaging tools, and four self-contained feature-chat handoffs.
- Seeded separate workstream objectives/achievements/current-task/architecture/manual-QA files.
- Baseline has 126 passing tests; no runtime feature implementation is included in this preparation.

## Parallel environments verified
- Created feature/integrations, feature/memory, feature/cron, and feature/skills in separate WSL folders.
- Bootstrapped isolated .venv environments without system ensurepip; packaging tools were downloaded once and installed offline into each environment.
- Verified correct imports from /tmp, disabled user site, senai help, and 126 passing baseline tests per worktree. Global editable installation was not changed.
- Completed four full handoffs, workstream progress templates, and shared-file ownership guidance. No feature code, live external service, or schedule was started.

## Modular merge guardrails
- Added machine-readable single-writer ownership, a shared merge policy, standardized per-feature delivery manifests, and a Git scope/readiness checker.
- TDD: scope-guard tests failed before implementation, covering core edits, rename deletions, untracked cross-feature paths, and shared-policy drift.
- Preserve active feature code and current interfaces; coordinator applies shared hooks/packaging/docs once during sequential integration.

## Merge policy synchronized
- Distributed identical coordinator rules/tooling and committed only those paths plus missing per-feature delivery records on all four active branches. No feature code was overwritten or rebased.
- All four ownership audits passed. Ten scope/readiness tests pass in each worktree; main regression suite has 136 passing tests.
- Feature manifests remain draft until module owners provide actual public API, dependencies, storage/migration, executor shape, and verification evidence.

## Installation memory integration (2026-11-09)

Added opt-in single-owner installation memory, global USER.md/MEMORY.md, persistent native-session snapshots and controlled learning. Existing unconfigured execution and Telegram state are preserved.

Integrated feature/memory through 3146de5 in merge 0f0c979. Coordinator lifecycle wiring: 62cbf9f. Feature scope/readiness passed before merge, with 176 offline tests (40 memory tests). Combined regression: 235 passed, including existing Telegram media/auth tests, 40 memory tests and 11 coordinator memory lifecycle tests. TDD logs include failing missing-runtime and SOUL-write tests before implementations.

Real isolated Codex acceptance at 62cbf9f: project A saved a harmless USER.md fact; a distinct fresh session in project B recalled it from the same installation. Exact-ID resume also succeeded. No production bot state, jobs, pairing, sessions or credentials were copied or used; no push, deployment or production restart.

Evidence:
- outputs/memory-combined-regression.log
- outputs/memory-transport-tests.log
- outputs/qa-memory-installation/acceptance.json
- outputs/qa-memory-installation/first-session.jsonl
- outputs/qa-memory-installation/final-fresh-session.jsonl
- outputs/qa-memory-installation/final-resume.jsonl

## Cron integration (2026-11-09)

Merged feature/cron through 46e739d (6a50762); wiring 7e6cf18. Consolidated pinned dependencies, shared senai cron management, opt-in /cron management, existing serialized native-session execution, and currently authorized durable text delivery. All 299 combined tests passed; installed CLI fixture QA and dependency checks passed. Production state/services untouched; live scheduling remains disabled and unverified. See projectprogress/cron.md for usage and limits.

## Supervised cron worker (2026-11-09)

Added explicit senai cron worker / worker-status commands in 58109c0. Execution and delivery loops are independent; scheduled native execution has a configurable process-group deadline. Unknown execution pauses the schedule and bypasses retries; ambiguous sends remain unknown. Singleton locking preserves Telegram's exact shared-session policy. Existing bot --enable-cron mode also drains delivery independently. All 312 tests passed, including disposable offline pipeline/authorized-delivery and restart acceptance. Live acceptance remains pending explicit instruction; production services/state were not used. Startup, shutdown and recovery: projectprogress/cron.md.

## Voice-only integration (2026-11-09)

Merged feature/integrations through fadeea4 (tested implementation c858952) in af84cc2. Feature scope/readiness and all 216 branch tests passed again. Resolved the Telegram CLI startup conflict by combining protected optional speech loading with existing cron deadlines and independent delivery callbacks. Added tests/coordination/test_voice_cron_composition.py for configured/unavailable speech alongside cron startup. All 345 combined tests passed. Logs: outputs/qa-integrations/coordinator-voice-review.log in the feature worktree, and outputs/voice-only-combined-regression.log plus outputs/voice-cron-composition.log on main.

Current /voice policy supersedes prior text-plus-audio documentation: audio only on successful upload, text fallback when unavailable/failing, no text acknowledgement, and persisted audio/fallback choice across delivery retries. Legacy partial text replies finish as text. Explicit /result still returns text. Optional local voice configuration commands are included; setup remains skippable. New voice_delivery storage is additive and media-local.

No Telegram credentials, production jobs/pairing/media/native authentication/session state were accessed or changed. No bot restart, live API test, push or deployment was performed. No further blocking code fixes found. Later operator-managed live QA should verify /voice QUESTION, bare /voice, explicit /result, unavailable-key fallback and restart/retry continuity. Network acceptance followed by local persistence failure remains an acknowledged ambiguity; no exactly-once claim.

Safely update the feature worktree using a fast-forward merge (do not rebase already-integrated history). The coordinator has NOT updated that worktree:
    cd /home/rk/SentiensHermes/senai-integrations
    git status --short
    git branch --show-current
Stop if the tree is not clean or the branch is not feature/integrations. Then:
    git merge --ff-only main
    source .venv/bin/activate
    python -m pip install -e .
    python -m pip check
    python -m unittest discover -s tests -v
    python scripts/check_workstream_scope.py --feature integrations --ready
Reinstalling in this worktree's .venv includes the cron dependencies now present on main; never use pip --user or reinstall globally. If fast-forward refuses because new feature commits were added, stop for coordinator review; do not reset or automatically rebase. These commands do not restart the bot or migrate live runtime state.

## Confirmed memory learning (2026-11-09)

Integrated 929a2ea in b6c56f7; successful-outcome evaluator wiring 4ffc1aa. Personal facts require explicit user retention confirmation; repetition never confirms. Only app-verified significant milestones qualify automatically. SOUL.md stays human-controlled. Installation-wide memory and frozen session snapshots preserved. Branch readiness/248 tests and combined 370 tests passed. See projectprogress/memory-learning.md. No push, deployment or production bot state used.

## New-user documentation and compatibility audit (2026-11-09)

Refreshed portable README/setup/command/compatibility/architecture/manual acceptance guides. Preserved earlier guides under projectprogress/history and labeled workstream records as historical. Parameterized contributor templates and removed user-wide install advice. Runtime source/scripts contain no developer-specific home paths. Updated CLI help to include memory and cron. Main and isolated fresh-checkout suites: 370 passed each. Local fresh clone dependency/install/entry-point checks passed; host ensurepip limitation is disclosed. No live providers, bot state or services used. No push performed.

## Friendly cron composition (2026-11-09)

Integrated friendly cron through c240922 (merge cdd0375, wiring ad81604). Authorized CLI destinations match account stores, with revocation checks at save; Telegram uses shared draft helpers for sequential creation, preview/confirmation/cancel/timeout and duplicate suppression. Saved timezone and explicit advanced local workflows preserved. Feature readiness/401 tests and combined 409 tests passed. No push, bot restart, live scheduling or production-state QA.

## Profiles and guarded Telegram composition

Integrated memory 94cb6f4 and integrations 2e09f9a; wiring 8fe1098. 474 combined offline tests passed. Profile shortcuts/setup, shared cron parser and durable conversation factory, explicit /new operators, startup pinning and foreground/cron/claim gating composed. Consolidated usage/API smoke tests and architecture in README.md. No push, production restart or live operation.

## Coordinator skills integration (2026-11-09)

Skills integrated through 82230b2 (tested feature source 4dbe998788e1601a464f4a7d26077848c19d7f32), merge 0667ad5, shared wiring 57d6c2e. Added singular basic skill list/use/import/show/export obsidian and plural advanced CLI. Consolidated PyYAML==6.0.3. Saved project selection feeds immutable exact-version/digest instructions/resources into the EXISTING executor, preserving native --skill, JSON options, memory, pairing and exact Telegram shared-session resume. Ordinary outcomes remain unverified without independently supplied Checks. No automatic proposal activation or model-prose verification. Obsidian path is prompted/saved on explicit export and shown on list/show; refresh stays explicit.

Verification: feature ownership/readiness passed; feature 272 tests passed when its own installed command and isolated config were used. Combined main 622 tests passed, including 9 new skills-composition tests and actual offline Telegram wrapper-child context/resume coverage. Dependency check passed. Initial non-isolated runs loaded operator defaults and failed; scripts/test.py now provides repeatable isolated tests, and the explicitly unconfigured test mocks configuration instead of assuming the user's home is empty. Logs: outputs/skills-combined-regression.log, skills-composition-green.log and skills-install.log. Historical feature handoff reports actual public import/model authoring/checked acceptance/reuse/rollback and user-confirmed Windows Obsidian viewing; those LIVE checks were not rerun by the coordinator.

Remaining explicit/separate paths: advanced skills run is a standalone authoring/evidence pipeline, not the Telegram session executor. Normal requests capture context/outcomes but do not create authoring run reports or auto-stage generated packages. Revision validation is a trusted Python callback/demo; no high-level validation wizard. No Telegram skill-management commands, vault watcher, automatic activation or weight training. Imported content is not security-scanned; origin/check records rely on trusted local state. No production state, live provider calls, push or deployment used.
