"""Feature-local explicit memory CLI; no routing or production session changes."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from senai.workspace import prepare_workspace
from .context import build_snapshot
from .store import MemoryStore, Namespace


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explicit project-scoped memory")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--scope", required=True)
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
        if args.command == "add":
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
    except (ValueError, KeyError, OSError, sqlite3.Error):
        # Do not echo memory, IDs, paths or database values through diagnostics.
        print("Memory operation failed: check input, capacity, namespace and storage.",
              file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
