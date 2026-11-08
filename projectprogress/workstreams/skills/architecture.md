# Skills architecture

Implemented: senai/skills/registry.py; public exports in senai/skills/__init__.py.

Registry(root) is an explicit isolated registry; callers should choose this worktree's outputs/. import_local(directory) snapshots regular files, validates SKILL.md, copies into a random registry-owned directory and activates one name in a SQLite transaction. Failed validation does not activate anything. Ordinary write/transaction failures clean up staged content; a process crash may leave inactive orphan directories, never intentionally selected entries. SQLite commits retain name, version, description, source absolute path, package digest and content directory. Imports never execute code.

list()/select(names) verify the stored full-package digest before returning frozen Skill records containing instructions and SKILL.md path. execute() is only an injected context boundary. Selection is explicit; no semantic matching, global discovery, native installation or replacement Codex executor.

Supported compatibility: deliberately restricted SKILL.md-style UTF-8 frontmatter. Opening/closing --- lines; required single-line name and description, optional version (default 1). Names are lowercase alphanumeric hyphen-separated, at most 64 characters; versions are bounded alphanumeric/dot/underscore/hyphen tokens. Simple quoted scalars supported. Unknown/duplicate keys, multiline/nested YAML and empty instructions rejected. This is not full YAML or a claim of universal Codex/Hermes package compatibility. Max 256 files, 1 MiB/file, 8 MiB/package. Auxiliary files are preserved. All source/content symlinks and archives are rejected. Duplicate names require a future explicit revision API rather than overwrite.

Trust boundary: instruction text remains untrusted content; syntax validation and hashes do not prove safe instructions. Caller controls selection/execution. Registry/source directories must not be concurrently modified by untrusted processes: filesystem snapshotting is not an OS isolation boundary or a defense against hostile file-replacement races. No evidence-based revision claims are made yet.

No third-party dependencies, downloaded references, authored reusable Codex skill, model calls, or sibling-feature imports used in this milestone. Remaining work is recorded in current task.md.

## Learning architecture and current step

Planned project layout: outputs/skills/registry.sqlite3 plus registry-owned package snapshot folders. Keep the existing package paths and import_local/list/select/execute contracts compatible. The SQLite outcomes table now stores immutable ID, skill name/version/digest, request, result, checks JSON, correction, derived status and UTC timestamp. outcomes(name) lists them in insertion order. No write happens merely by importing the Python package.

Check(name, passed, evidence) is a frozen record supplied by a trusted adapter. record_outcome(name, *, digest, request, result, checks=(), correction="") validates bounded text, boolean check results and active content identity. No checks means unverified; all checks passing means passed; any failing check means failed. These labels describe supplied checks, not universal task correctness or authenticated evidence. Recording does not change selected instructions. No raw production transcript, credentials, or live state is gathered automatically.

Future tables: immutable revision candidates with base digest and outcome links, regression evidence, active revision pointer and activation/rollback audit history. Future loop: select -> existing execution -> observed checks -> append outcome -> Codex-generated proposal -> isolated regression checks -> activate -> reuse. No model weights are changed. The coordinator owns insertion of shared post-execution hooks; this feature supplies injected interfaces only.

Research sources read 2026-11-09: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills ; https://hermes-agent.nousresearch.com/docs/user-guide/features/memory ; https://agentskills.io/specification . Hermes uses procedural skills, progressive disclosure and agent-managed/background revisions; our proposed explicit regression gate and immutable history are project design choices, not a claim to duplicate Hermes implementation. Metadata-only catalog/resource loading and broader frontmatter compatibility remain future work.

## Implemented revision proposal step

propose_revision(name, *, document, outcome_ids, reason) accepts a complete replacement SKILL.md string and returns frozen Revision. It preserves every supporting file from the current skill package. Candidate metadata must keep the same name, use a distinct bounded version, and change instruction text. Version ordering is not inferred; duplicate versions for a skill are rejected.

The additive revisions table stores ID, skill name/version, base digest, candidate digest, original source, ordered outcome-ID links, reason, package directory and UTC timestamp. A UNIQUE(skill_name, version) constraint reserves versions. Proposal insertion is transactional with an active-base recheck; ordinary failures remove staged package folders. As with imports, a hard process crash can leave an inactive orphan folder. No selection pointer changes.

Evidence must be nonempty, unique and already recorded as passed/failed for this exact skill digest; unverified prose and other-skill evidence cannot support proposals. This is validation of trusted-adapter records, not independent authentication of evidence. No LLM drafting occurs in this API. revisions(name) returns proposals in insertion order after verifying full candidate content hashes and metadata. select/execute continue to expose only the original active skill.

Revision packages are currently instruction-only changes: support files cannot be added/edited through proposal creation. Candidate regression validation, activation, rollback and audit events remain pending. Revision is publicly exported from senai.skills. Existing skills/outcomes schemas and public signatures are unchanged.

## Implemented regression validation step

validate_revision(revision_id, *, validator) calls trusted validator(base, candidate, outcomes) and returns frozen Validation. The inputs are exact base Skill, proposed Revision and ordered tuple of linked Outcome records. Return an iterable of Check records with observed evidence. At least one check is required; callers should cover both old successful behavior and the corrected failure. Selecting meaningful cases is the caller's responsibility; a passing label is not universal improvement proof.

The additive validations table retains ID, revision ID, base/candidate digests, checks JSON, passed/failed/error status, sanitized error description and UTC timestamp. Failed checks are recorded as failed. Empty/malformed returns and ordinary checker exceptions are recorded as error with no raw exception message. KeyboardInterrupt/SystemExit propagate. validations(revision_id) retains every attempt in insertion order; a future activation gate must use the latest attempt, never an earlier pass after a failure.

Hashes are checked before and after the callback; changing candidate/base bytes prevents saving a pass. Active base is rechecked transactionally before result insertion. This is content identity verification, not OS sandboxing. The injected checker runs in the caller process and must supply its own isolated evaluation; no imported script is executed automatically. All proposals remain inactive, including passing ones. Shared Check validation is reused for outcomes and regression checks.

Public frozen Validation fields: id, revision_id, base_digest, candidate_digest, checks, status, error, created_at. Initialization creates the local validations table/index idempotently, leaving existing tables and records intact.

## Implemented activation and rollback step

activate_revision(revision_id) -> Skill explicitly moves the current skills row to the proposed package only if its base is still current and its latest validation attempt passed for the exact base and candidate digests. Full-package hashes and metadata are checked. Accepted-version insertion, active-row update and audit event commit atomically. A new failure/error after an earlier pass blocks activation. A sibling proposal becomes stale after another revision activates.

accepted_versions stores immutable accepted package references (name, version, description, source, digest, directory, accepted_at), unique per skill/version and skill/digest. Initial local imports are accepted baselines; syntax validation does not establish behavior. Existing registry active rows are backfilled idempotently on construction without losing previous outcomes/proposals/results. New proposals cannot reuse any accepted version identifier.

activation_history retains Activation(id, skill_name, action, from_digest, to_digest, revision_id, validation_id, reason, created_at). Actions are import, activate and rollback. history(name) reads audits even if current content is damaged. versions(name) lists accepted packages in first-acceptance order and verifies their contents; proposals are excluded.

rollback(name, *, digest, reason) restores an intact accepted package for the same skill, with a required rationale. Never-accepted candidates and current-version no-ops are rejected. It verifies only the destination bytes so that a damaged current package can be recovered. Rollback changes no file bytes and deletes no outcome/validation/history records. It can return to any previously accepted version (including a newer accepted version); this is restoration, not a new validation claim.

Revision.status now reports proposed, active or accepted according to recorded acceptance and current selection. Individual revision lookup validates only the requested package, allowing intact revisions/rollback to work despite unrelated damaged proposals. Registry select/execute retain their signatures and supply the currently active package.

No sandbox is introduced: registry directories remain trusted against hostile concurrent filesystem replacement. SQLite guards active-state updates but cannot provide an OS boundary around callbacks/files. No global Codex skills installed or shared execution/CLI code edited.

## Feature-local terminal interface

`python -m senai.skills --project EXISTING_PROJECT COMMAND` uses only that project's outputs/skills/ registry. Commands: import SOURCE_DIRECTORY, list, show NAME, context NAME REQUEST, outcomes NAME, versions NAME, history NAME, revisions NAME, validations REVISION_ID, activate REVISION_ID, rollback NAME --digest DIGEST --reason REASON, demo. Output is JSON; operational errors return 2 with a short stderr message. Help and listing a missing registry create no state. Import never executes code. Existing outputs symlinks are rejected through the stable workspace policy; global skills are untouched.

list emits active metadata without instruction text. show emits selected instructions, paths and provenance. context exports a request and one selected Skill through the existing injected executor seam; it deliberately makes no model call. Actual Codex use still needs an adapter. Candidate authoring and regression checking are currently Python APIs rather than user-supplied CLI check-result flags.

senai/skills/demo.py run_demo(project) creates a new retained outputs/skills-demo/run-*/ project, its fixture and its own outputs/skills registry. It records a synthetic failure, proposes instructions, injects a simulated passing regression, activates v2, restores v1 and reopens the registry. Mode and limitations are explicit in output. It never touches the normal project skill registry and never invokes a model/script. Repeated runs use separate folders. CLI entrypoint is senai/skills/__main__.py and main(argv=None, stdout=None, stderr=None) in cli.py. No shared console-entrypoint/package edits.

## Evidence-guided reviewer adapter

review_skill(registry, name, *, outcome_ids, reviewer) -> ReviewResult. reviewer(prompt: str) -> str JSON receives only the exact active SKILL.md and selected previously observed passed/failed Outcome records. No unverified, duplicate, missing or wrong-base evidence accepted. Budget: at most 100 selected IDs and 128 KiB total encoded prompt; oversize input is rejected before model use, not silently truncated. Caller must redact private data before recording evidence. No unrelated outcomes or filesystem paths are automatically added.

The prompt preserves user scope/permissions, asks for a narrow justified correction, forbids invented results and leaves supporting files unchanged. It allows no_change when evidence is insufficient. Target version is a fresh opaque r-UUID, not an inferred semantic increment. Response schema has exactly action, reason, document strings. Duplicate/unknown keys, malformed replies, unsupported metadata or wrong identity/version are rejected. A successful revise result passes through propose_revision and cannot create a passing validation. Model self-evaluation is not regression evidence. No-change results are returned to caller; no separate durable review-attempt log is added in this step. Revision rationale/evidence links persist for generated proposals.

ReviewResult(status, reason, revision) is frozen, with status proposed or no_change and revision possibly None. Active skill identity is rechecked after review so stale answers cannot be attached to a new base. Ordinary reviewer errors are converted to a generic SkillError without raw diagnostic text; there is no automatic retry or looping cost.

review_with_codex(registry, name, *, outcome_ids, project, model=None, executor=None) -> ReviewResult uses only the stable senai.codex.run_codex/ CodexOptions interfaces. Registry must be within the chosen real project outputs/. It creates a temporary .skills-review-* workspace/schema there, requests sandbox read-only, approval never, skip-git check and --output-schema, with an optional explicit model. No resume/--last is used for this separate one-shot review; shared bot-session mappings are untouched. executor can inject the existing run_codex signature for tests. Native config/auth/tool settings still apply; neither prompt text nor read-only mode independently isolates configured remote tools. No global skills/config/auth are modified by this module. Native CLI can retain its ordinary session history.

CLI review is opt-in and potentially a real authenticated model call. The offline demo remains synthetic and never starts it. Existing context command still only exports instructions. No shared execution trigger is installed.

Sources consulted for this step (2026-11-09): official https://learn.chatgpt.com/docs/non-interactive-mode and https://learn.chatgpt.com/docs/build-skills ; local system openai-docs/SKILL.md and skill-creator/SKILL.md. Applied narrow evidence-guided revisions and progressive-disclosure/scope guidance; these do not establish behavioral improvement. Installed parser flags were independently inspected, not assumed from online docs.
