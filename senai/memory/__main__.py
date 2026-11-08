"""Feature-local explicit memory CLI; no routing or production session changes."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from senai.workspace import prepare_workspace
from .context import build_snapshot
from .store import MemoryStore, Namespace
from .profiles import ProfileStore, ProfileProposal
from .session import start_session


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explicit project-scoped memory")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--user-id", help="Authorized identity; never inferred from prompt text")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("add", "update"):
        child = sub.add_parser(command)
        if command == "update":
            child.add_argument("id")
        child.add_argument("text")
        child.add_argument("--provenance", required=True)
    sub.add_parser("list")
    child = sub.add_parser("delete")
    child.add_argument("id")
    child = sub.add_parser("context")
    child.add_argument("request")
    child.add_argument("--max-chars", type=int, default=2200)
    child = sub.add_parser("profile-show")
    child.add_argument("name", choices=("SOUL.md", "USER.md", "MEMORY.md"))
    child = sub.add_parser("profile-propose")
    child.add_argument("name", choices=("SOUL.md", "USER.md", "MEMORY.md"))
    child.add_argument("text", help="Empty string proposes deletion")
    child.add_argument("--origin", choices=("human", "outcome"), default="human")
    child.add_argument("--verified", action="store_true", help="Trusted validator confirmed outcome")
    child = sub.add_parser("profile-apply")
    child.add_argument("proposal", type=Path)
    child.add_argument("--approve", action="store_true")
    child = sub.add_parser("session-context")
    child.add_argument("request")
    child.add_argument("--include-user", action="store_true",
                       help="Only for a session authorized to see this user's profile")
    child.add_argument("--max-chars", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        namespace = Namespace(args.project, args.scope)
        workspace = prepare_workspace(args.project)
        directory = workspace / ".senai-memory"
        if directory.is_symlink():
            raise ValueError("memory directory must not be a symlink")
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory / "memory.db"
        if path.is_symlink():
            raise ValueError("memory database must not be a symlink")
        store = MemoryStore(path)
        path.chmod(0o600)
        profiles = ProfileStore(directory / "profiles", namespace, user_id=args.user_id)
        if args.command == "profile-show":
            document = profiles.read(args.name)
            result = asdict(document)
            result["path"] = str(document.path)
        elif args.command == "profile-propose":
            result = asdict(profiles.propose(args.name, args.text, origin=args.origin, verified=args.verified))
        elif args.command == "profile-apply":
            with args.proposal.open("rb") as stream:
                payload = stream.read(100001)
            if len(payload) > 100000:
                raise ValueError("proposal exceeds input limit")
            proposal = ProfileProposal(**json.loads(payload))
            result = asdict(profiles.apply(proposal, approved=args.approve))
            result["path"] = str(result["path"])
        elif args.command == "session-context":
            snapshot = start_session(profiles, store, args.request,
                                     include_user=args.include_user, max_chars=args.max_chars)
            print(snapshot.context)
            return 0
        elif args.command == "add":
            result = asdict(store.add(namespace, args.text, provenance=args.provenance))
        elif args.command == "update":
            result = asdict(store.update(namespace, args.id, args.text,
                                         provenance=args.provenance))
        elif args.command == "delete":
            result = {"deleted": store.delete(namespace, args.id)}
        elif args.command == "list":
            result = [asdict(entry) for entry in store.list(namespace)]
        else:
            print(build_snapshot(store, namespace, args.request, max_chars=args.max_chars))
            return 0
        print(json.dumps(result))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error):
        # Do not echo memory, IDs, paths or database values through diagnostics.
        print("Memory operation failed: check input, capacity, namespace and storage.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
