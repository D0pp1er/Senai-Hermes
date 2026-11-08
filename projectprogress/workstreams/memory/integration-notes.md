# Memory integration contract

## Minimal coordinator hook (proposed, not applied)

After authorization, canonical project/scope selection and prepare_workspace, create:
- MemoryStore(workspace / ".senai-memory" / "memory.db")
- ProfileStore(workspace / ".senai-memory" / "profiles", namespace, user_id=authorized_user_or_none)

Validate/reject symlinked state roots and DB as the feature-local CLI does. Direct callers
own their state location and access permissions. Never infer scope/user identity from
model output. ProfileStore validates its paths; no recursive context discovery.

For a genuinely fresh native session:
    snapshot = start_session(profiles, store, request, include_user=False, max_chars=8000)
    result = execute_session(request, workspace, snapshot=snapshot,
                             executor=run_codex, options=options, skills=skills)

Use include_user=True only in an authorized private session with an explicit user_id.
USER.md is project/scope/user-specific. SOUL.md and MEMORY.md are project/scope-specific.
Never include a private USER.md in Telegram's configured shared conversation.

Retain the same snapshot object for later turns in that native session. A new session
or explicit authorized refresh calls start_session again. Persisting snapshot-to-native-
session mappings across wrapper process restarts is coordinator work, not implemented
here. Do not silently reload files into a resumed native session. Keep existing Telegram
session ID behavior. No automatic reset/resume changes are required by this module.

The older execute_with_memory API stays unchanged for SQLite-only callers. The new
session API is additive; do not combine both bridges or build_prompt twice.
Executor is synchronous run_codex(prompt, workspace, **kwargs) -> str; exceptions propagate.

## Update rules

SOUL.md: explicit human authorship only. USER.md: reviewed stable preferences, private
to project/scope/user. MEMORY.md: reviewed curated project summary.
SQLite: detailed facts with IDs/provenance/timestamps. No automatic file/DB mirroring.
The same fact should have one authoritative home; semantic duplicate detection is not
implemented. File updates are complete replacement proposals, with visible unified diffs.

propose(name, text, origin="human", verified=False) only creates a volatile proposal.
Outcome-origin proposals require a trusted validator's verified=True; SOUL.md rejects
outcome origin even when verified. apply(proposal, approved=True) checks owner, validation,
and previous content hash under a cooperative process lock, then atomically replaces
the file. Empty replacement text deletes the file. An explicit human approval path is
required; model output is neither verification nor permission. Fields are not signatures:
trusted local caller/authentication is the boundary.

## Storage, dependencies, compatibility

No new dependency; standard-library fcntl means WSL/POSIX is required.
SQLite remains schema v1; no migration of existing entries/native/Telegram state.
Optional files live at profiles/<sha256(project,scope)>/{SOUL.md,MEMORY.md}, and
profiles/<sha256(project,scope)>/users/<sha256(user_id)>/USER.md.
Missing files are valid and existing SQLite users need no setup.
No starter personality is silently created and no external home/profile files imported.

Shared proposals only: coordinator may add top-level command routing and session lifecycle
adapter. No sibling modules required. No shared/core files changed by this workstream.

## Limitations

Files: UTF-8, maximum 4000 characters / 16000 bytes each; fixed allowlist.
Total session context default 8000 chars including source metadata/escaping. Curated files
must fit in full; overflow errors. SQLite results fill remaining space and may be omitted.
SOUL guidance is subordinate to higher instructions and authorization; factual sources
are untrusted reference data. Labels do not guarantee model resistance to prompt injection.
Changes are visible to new snapshots only. File locks coordinate our writers; unrelated
manual editors do not participate in the lock. Hash checks catch prior edits, not hostile
races or cross-file transactions from external editors. Atomic replace prevents partial
files; this is not a version-history or disaster-recovery system.
Credential pattern filters are incomplete. Storage is unencrypted; deletion is not secure
erasure and cannot retract previously supplied context. No live model test or session
lifecycle integration has been performed.
