"""Human profile shortcuts with injected streams; coordinator supplies saved installation."""
import argparse
import os
import re
from functools import partial
from pathlib import Path

from .installation import _InstallationProfiles
from .profiles import ConflictError, _safe_path
from .store import Namespace, validate_text


_PROFILES = {"memory": "MEMORY.md", "user": "USER.md", "soul": "SOUL.md"}
_EXAMPLES = {"memory": "Finished the first release", "user": "Prefers concise replies",
             "soul": "Be clear and thoughtful"}


class _CommandError(ValueError):
    pass


class _ParseExit(Exception):
    def __init__(self, status):
        self.status = status


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args, out, err, **kwargs):
        super().__init__(*args, **kwargs)
        self.out, self.err = out, err

    def print_help(self, file=None):
        super().print_help(file or self.out)

    def error(self, message):
        # Do not echo potentially sensitive unknown arguments.
        print(f"Use {self.prog} add TEXT, show, path or setup. See --help.", file=self.err)
        raise _ParseExit(2)

    def exit(self, status=0, message=None):
        if message:
            print(message, file=self.err, end="")
        raise _ParseExit(status)


def _profiles(installation, *, create=False):
    if installation is None or (isinstance(installation, str) and not installation.strip()):
        raise _CommandError("No installation configured. Run senai setup first.")
    root = Path(installation).expanduser().absolute()
    _safe_path(root)
    if root.exists() and not root.is_dir():
        raise _CommandError("Installation path is not a directory. Run senai setup with a folder.")
    if not root.exists() and not create:
        raise _CommandError("Installation folder is missing. Run senai setup or the profile setup command.")
    directory = root / "outputs" / ".senai-memory"
    _safe_path(directory)
    for parent in (root / "outputs", directory):
        if parent.exists() and not parent.is_dir():
            raise _CommandError("Profile storage path is not a directory. Check the installation setup.")
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root = root.resolve()
    return _InstallationProfiles(root / "outputs" / ".senai-memory",
                                 Namespace(root, "installation"), user_id="owner")


def setup_profiles(installation):
    """Explicit setup: create missing installation/profile paths; preserve existing files.

    Return {filename: absolute Path}. No defaults, SQLite, session or environment changes.
    """
    profiles = _profiles(installation, create=True)
    with profiles._lock():
        # Validate all existing files before creating any missing files.
        documents = [profiles.read(name) for name in _PROFILES.values()]
        for document in documents:
            try:
                fd = os.open(document.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600)
            except FileExistsError:
                profiles.read(document.name)
            else:
                os.close(fd)
    return {document.name: document.path for document in documents}


def _append_human(profiles, name, text):
    text = validate_text(text, "profile text", 4000)
    before = profiles.read(name)
    key = " ".join(text.split()).casefold()
    records = re.split(r"(?m)^- ", before.text) + before.text.splitlines()
    existing = {" ".join(record.strip().removeprefix("- ").split()).casefold()
                for record in records}
    if key in existing or key == " ".join(before.text.split()).casefold():
        return False
    block = "- " + text
    combined = before.text + "\n\n" + block if before.text else block
    if len(combined) > 4000:
        raise _CommandError("Profile is full (4000-character limit). Use the path command to shorten it.")
    proposal = profiles.propose(name, combined, origin="human")
    if proposal.before_revision != before.revision:
        raise ConflictError("profile changed")
    profiles.apply(proposal, approved=True)
    return True


def profile_main(kind, argv, *, installation, stdin, stdout, stderr) -> int:
    """Handle an explicitly HUMAN memory/user/soul add/show/path/setup command.

    The root router must never invoke this shortcut for autonomous learning.
    Existing advanced python -m senai.memory routes remain unchanged.
    """
    if not isinstance(kind, str) or kind not in _PROFILES:
        print("Choose memory, user or soul.", file=stderr)
        return 2
    parser = _Parser(prog="senai " + kind, out=stdout, err=stderr,
                     description="Edit this installation's human profile. New sessions load changes.")
    sub = parser.add_subparsers(dest="command", required=True,
                                parser_class=partial(_Parser, out=stdout, err=stderr))
    child = sub.add_parser("add", help="Append an explicit human-authored note")
    child.add_argument("text", nargs="*")
    sub.add_parser("show", help="Show the saved text")
    sub.add_parser("path", help="Print the absolute path for direct editing")
    sub.add_parser("setup", help="Create missing profile paths without overwriting")
    name = _PROFILES[kind]
    try:
        args = parser.parse_args(argv)
        if args.command == "setup":
            for filename, path in setup_profiles(installation).items():
                print(f"{filename}: {path}", file=stdout)
            print("Existing text preserved. New text is loaded by a fresh session.", file=stdout)
            return 0
        profiles = _profiles(installation)
        path = profiles._path(name)
        if args.command == "path":
            print(path, file=stdout)
            return 0
        if args.command == "show":
            document = profiles.read(name)
            print(document.text or f"{name} is empty. Add text with senai {kind} add.",
                  file=stdout)
            return 0
        if not profiles.root.is_dir():
            raise _CommandError(f"Profiles are not initialized. Run senai {kind} setup.")
        if args.text:
            text = " ".join(args.text)
        elif not stdin.isatty():
            raise _CommandError(f'Provide text, for example: senai {kind} add "{_EXAMPLES[kind]}". '
                                "Run without TEXT in an interactive terminal to be prompted.")
        else:
            print(f'{name} text (example: "{_EXAMPLES[kind]}"): ', file=stdout, end="", flush=True)
            text = stdin.readline(4002)
        if not text.strip():
            raise _CommandError("No text entered; nothing saved.")
        if _append_human(profiles, name, text):
            print(f"Added to {name}: {path}", file=stdout)
        else:
            print(f"Already present in {name}; nothing added.", file=stdout)
        print("Existing sessions keep their frozen context. Start a fresh session to load changes.",
              file=stdout)
        return 0
    except _ParseExit as exc:
        return exc.status
    except KeyboardInterrupt:
        print("Cancelled; nothing saved.", file=stderr)
        return 130
    except ConflictError:
        print(f"{name} changed during this update; nothing overwritten. "
              f"Run senai {kind} show, then retry.", file=stderr)
    except _CommandError as exc:
        message = str(exc)
        if "full" in message:
            message = f"{name} is full (4000-character limit). Run senai {kind} path and shorten it."
        print(message, file=stderr)
    except PermissionError:
        print("Permission denied. Check installation/profile permissions.", file=stderr)
    except IsADirectoryError:
        print(f"{name} must be a regular file, not a directory. Check senai {kind} path.", file=stderr)
    except (ValueError, TypeError) as exc:
        # Library validation errors contain fixed diagnostics, never the rejected text.
        message = str(exc) if isinstance(exc, ValueError) else "Invalid installation path."
        print(f"Profile not saved: {message}. Check text or senai {kind} path.", file=stderr)
    except OSError:
        print("Cannot access profile storage. Check its paths and permissions; run senai setup.",
              file=stderr)
    return 2
