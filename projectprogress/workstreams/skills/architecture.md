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
