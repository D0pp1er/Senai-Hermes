"""Project-local registry CLI, separate from the coordinator-owned senai router."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from senai.workspace import prepare_workspace
from .registry import Registry, SkillError
from .demo import run_demo
from .review import review_with_codex


def _parser():
    parser = argparse.ArgumentParser(prog="python -m senai.skills", description="Manage isolated project skills. Context export does not execute Codex.")
    parser.add_argument("--project", default=".", help="Existing project; registry is outputs/skills/")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List active skills without loading their instructions into output")
    importer = commands.add_parser("import", help="Import a local SKILL.md package directory; never runs code")
    importer.add_argument("source")
    for name in ("show", "metadata", "versions", "history", "revisions", "outcomes"):
        command = commands.add_parser(name)
        command.add_argument("name")
    for name in ("validations", "activate"):
        command = commands.add_parser(name)
        command.add_argument("revision_id")
    rollback = commands.add_parser("rollback", help="Restore an accepted package by its full digest")
    rollback.add_argument("name")
    rollback.add_argument("--digest", required=True)
    rollback.add_argument("--reason", required=True)
    context = commands.add_parser("context", help="Export request plus one selected skill; does not run a model")
    context.add_argument("name")
    context.add_argument("request")
    review = commands.add_parser("review", help="Explicit Codex call: propose an inactive update from selected saved outcomes")
    review.add_argument("name")
    review.add_argument("--outcome", dest="outcome_ids", action="append", required=True)
    review.add_argument("--model", default=None)
    commands.add_parser("demo", help="Run and retain an isolated synthetic offline lifecycle demo")
    return parser


def _record(value, *, instructions=True):
    result = asdict(value)
    if not instructions:
        result.pop("instructions", None)
    return result


def main(argv=None, stdout=None, stderr=None):
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    args = _parser().parse_args(argv)
    try:
        project = Path(args.project).expanduser().resolve()
        if not project.is_dir():
            raise SkillError("Project must be an existing directory")
        outputs = project / "outputs"
        if outputs.is_symlink():
            raise SkillError("outputs must be a real directory, not a symlink")
        path = outputs / "skills"
        if args.command == "demo":
            result = run_demo(project)
        elif args.command == "list" and not path.exists() and not path.is_symlink():
            result = []
        else:
            if args.command != "import" and not path.exists():
                raise SkillError("No saved skills registry; import a local package first")
            if args.command == "import":
                prepare_workspace(project)
            registry = Registry(path)
            if args.command == "import":
                result = _record(registry.import_local(Path(args.source).expanduser()), instructions=False)
            elif args.command == "list":
                result = [_record(skill, instructions=False) for skill in registry.list()]
            elif args.command == "show":
                result = _record(registry.select([args.name])[0])
            elif args.command == "metadata":
                result = registry.metadata(args.name)
            elif args.command in {"versions", "history", "revisions", "outcomes"}:
                result = [_record(value) for value in getattr(registry, args.command)(args.name)]
            elif args.command == "validations":
                result = [_record(value) for value in registry.validations(args.revision_id)]
            elif args.command == "activate":
                result = _record(registry.activate_revision(args.revision_id), instructions=False)
            elif args.command == "rollback":
                result = _record(registry.rollback(args.name, digest=args.digest, reason=args.reason), instructions=False)
            elif args.command == "review":
                result = _record(review_with_codex(registry, args.name, outcome_ids=args.outcome_ids, project=project, model=args.model))
            elif args.command == "context":
                result = registry.execute(args.request, [args.name], executor=lambda request, skills: {"request": request, "skills": [_record(skill) for skill in skills]})
            else:
                raise SkillError("Unsupported command")
        print(json.dumps(result, default=str, indent=2), file=out)
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print("skills: " + str(exc), file=err)
        return 2
