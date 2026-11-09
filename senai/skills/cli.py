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
from .live_demo import run_live_demo
from .review import review_with_codex
from .run import run_request, expected_files_checker
from .learning import check_with_codex
from .obsidian import export_vault


def _parser():
    parser = argparse.ArgumentParser(prog="python -m senai.skills", description="Manage isolated project skills. Context export does not execute Codex.")
    parser.add_argument("--project", default=".", help="Existing project; registry is outputs/skills/")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export-obsidian", help="Create/refresh a Markdown vault with skill origins and concise history")
    export.add_argument("--destination", default=None, help="Dedicated local vault folder; Windows C:\\ paths or WSL /mnt/c paths accepted")
    commands.add_parser("list", help="List active skills without loading their instructions into output")
    importer = commands.add_parser("import", help="Import a local SKILL.md package directory; never runs code")
    importer.add_argument("source")
    github = commands.add_parser("import-github", help="Import a public GitHub package pinned to an exact commit")
    github.add_argument("repository", help="owner/repo (no URL or credentials)")
    github.add_argument("--commit", required=True, help="Exact 40-character lowercase commit SHA")
    github.add_argument("--path", required=True, help="Package directory inside repository, or . for root")
    for name in ("show", "metadata", "origin", "versions", "history", "revisions", "outcomes"):
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
    commands.add_parser("learning", help="List inactive and accepted locally authored candidates")
    learn = commands.add_parser("learn", help="Stage a generated package from a checked saved run; does not activate")
    learn.add_argument("--run", dest="run_id", required=True)
    learn.add_argument("--path", required=True, help="Relative package directory inside source run workspace")
    learn.add_argument("--reason", required=True)
    checking = commands.add_parser("check-learning", help="Use Codex on explicit JSON test cases; compare results independently")
    checking.add_argument("candidate_id")
    checking.add_argument("--cases", required=True, help="JSON list: name, request, expected_json per case")
    checking.add_argument("--model", default=None)
    for name in ("accept-learning", "learning-checks"):
        learning_command = commands.add_parser(name)
        learning_command.add_argument("candidate_id")
    run = commands.add_parser("run", help="Run an ordinary request with saved skills; artifacts retained under outputs/skill-runs")
    run.add_argument("name", help="Primary saved skill")
    run.add_argument("request")
    run.add_argument("--skill", action="append", default=[], help="Additional saved skill; repeatable")
    run.add_argument("--native-skill", action="append", default=[], help="Additional installed native skill; repeatable")
    run.add_argument("--model", default=None)
    run.add_argument("--read-only", action="store_true")
    run.add_argument("--expect-file", action="append", default=[], help="Explicit relative artifact existence check, not a correctness proof")
    demo = commands.add_parser("demo", help="Run an isolated demo; --live uses installed Codex with actual output checks")
    demo.add_argument("--live", action="store_true", help="Make up to four live Codex calls on a controlled fixture")
    demo.add_argument("--model", default=None)
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
            if args.live:
                result = run_live_demo(project, model=args.model, emit=lambda message: print(message, file=err, flush=True))
            else:
                result = run_demo(project)
        elif args.command == "list" and not path.exists() and not path.is_symlink():
            result = []
        else:
            if args.command not in {"import", "import-github"} and not path.exists():
                raise SkillError("No saved skills registry; import a local package first")
            if args.command in {"import", "import-github"}:
                prepare_workspace(project)
            registry = Registry(path)
            if args.command == "import":
                result = _record(registry.import_local(Path(args.source).expanduser()), instructions=False)
            elif args.command == "import-github":
                result = _record(registry.import_github(args.repository, commit=args.commit, path=args.path), instructions=False)
            elif args.command == "list":
                result = []
                for skill in registry.list():
                    record = _record(skill, instructions=False)
                    origin = registry.origin(skill.name)
                    record.update(origin=origin.kind, source_kind=origin.source_kind, locally_revised=origin.locally_revised)
                    result.append(record)
            elif args.command == "show":
                result = _record(registry.select([args.name])[0])
            elif args.command == "export-obsidian":
                result = _record(export_vault(registry, project=project, destination=args.destination))
            elif args.command == "origin":
                result = _record(registry.origin(args.name))
            elif args.command == "learning":
                result = [_record(candidate) for candidate in registry.learning_candidates()]
            elif args.command == "learn":
                result = _record(registry.stage_learning(args.run_id, path=args.path, reason=args.reason))
            elif args.command == "check-learning":
                cases_path = Path(args.cases).expanduser()
                if not cases_path.is_file() or cases_path.stat().st_size > 64000:
                    raise SkillError("Cases must be a JSON file up to 64,000 bytes")
                cases = json.loads(cases_path.read_text(encoding="utf-8"))
                result = _record(check_with_codex(registry, args.candidate_id, cases=cases, project=project, model=args.model))
            elif args.command == "accept-learning":
                accepted = registry.accept_learning(args.candidate_id)
                result = _record(accepted, instructions=False)
                result["origin"] = _record(registry.origin(accepted.name))
            elif args.command == "learning-checks":
                result = [_record(value) for value in registry.learning_checks(args.candidate_id)]
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
            elif args.command == "run":
                checker = expected_files_checker(args.expect_file) if args.expect_file else None
                result = _record(run_request(registry, args.request, [args.name, *args.skill], project=project, model=args.model, read_only=args.read_only, native_skills=tuple(args.native_skill), checker=checker))
            elif args.command == "context":
                result = registry.execute(args.request, [args.name], executor=lambda request, skills: {"request": request, "skills": [_record(skill) for skill in skills]})
            else:
                raise SkillError("Unsupported command")
        print(json.dumps(result, default=str, indent=2), file=out)
        if args.command == "check-learning" and result["status"] != "passed":
            return 2
        if args.command == "run" and result["status"] != "completed":
            return 2
        return 2 if args.command == "demo" and args.live and result.get("status") != "completed" else 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print("skills: " + str(exc), file=err)
        return 2
