# Skills architecture

Implemented: senai/skills/registry.py; public exports in senai/skills/__init__.py.

Registry(root) is an explicit isolated registry; callers should choose this worktree's outputs/. import_local(directory) snapshots regular files, validates SKILL.md, copies into a random registry-owned directory and activates one name in a SQLite transaction. Failed validation does not activate anything. Ordinary write/transaction failures clean up staged content; a process crash may leave inactive orphan directories, never intentionally selected entries. SQLite commits retain name, version, description, source absolute path, package digest and content directory. Imports never execute code.

list()/select(names) verify the stored full-package digest before returning frozen Skill records containing instructions and SKILL.md path. execute() is only an injected context boundary. Selection is explicit; no semantic matching, global discovery, native installation or replacement Codex executor.

Supported compatibility: deliberately restricted SKILL.md-style UTF-8 frontmatter. Opening/closing --- lines; required single-line name and description, optional version (default 1). Names are lowercase alphanumeric hyphen-separated, at most 64 characters; versions are bounded alphanumeric/dot/underscore/hyphen tokens. Simple quoted scalars supported. Unknown/duplicate keys, multiline/nested YAML and empty instructions rejected. This is not full YAML or a claim of universal Codex/Hermes package compatibility. Max 256 files, 1 MiB/file, 8 MiB/package. Auxiliary files are preserved. All source/content symlinks and archives are rejected. Duplicate names require a future explicit revision API rather than overwrite.

Trust boundary: instruction text remains untrusted content; syntax validation and hashes do not prove safe instructions. Caller controls selection/execution. Registry/source directories must not be concurrently modified by untrusted processes: filesystem snapshotting is not an OS isolation boundary or a defense against hostile file-replacement races. No evidence-based revision claims are made yet.

No third-party dependencies, downloaded references, authored reusable Codex skill, model calls, or sibling-feature imports used in this milestone. Remaining work is recorded in current task.md.
