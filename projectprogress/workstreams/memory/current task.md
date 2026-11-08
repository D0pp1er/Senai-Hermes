# Current task

Branch: feature/memory
Worktree: /home/rk/SentiensHermes/senai-memory
Status: scoped handoff complete; ready for coordinator review.

Verified .venv Python and senai.__file__ point here, including when invoked from /tmp.
126 baseline + 18 memory tests = 144 offline tests passing.
No shared/core files edited; no branch switches, merge, push or production services.

## Minimal proposed shared integration

After authorization and prepare_workspace(project), construct Namespace(project, scope)
from trusted request routing, never from model output. Derive MemoryStore at
outputs/.senai-memory/memory.db (reject symlinked state as the local CLI does).

Call:
    execute_with_memory(request, workspace, store=store, namespace=namespace,
                        executor=run_codex, options=options, skills=skills,
                        stdout=stdout, stderr=stderr)

The existing run_codex shape remains unchanged. This feature imports build_prompt;
do not build the ordinary prompt twice. Default maximum context is 2200 characters.
For native resumed chats, decide snapshot lifecycle explicitly at integration; this
branch neither changes Telegram nor assumes resume constitutes durable memory.

Only a trusted validation result may supply verified=True to extract_candidates.
Present candidates for explicit approval; accept_candidate(..., approved=True) saves
one fact in its original namespace. A model's success string is not validation.
Do not automatically save raw outputs. Candidate rejection requires no DB operation.

Dependencies: Python standard library only; no requirements-memory.txt needed.
Migration: separate new SQLite database, schema user_version=1; no existing databases
touched. Unsupported versions/corrupt storage fail rather than resetting data.
Coordinator owns top-level CLI packaging/routes; python -m senai.memory works now.
