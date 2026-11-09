"""Feature-local demonstration of profile shortcuts before coordinator root routing."""
import argparse
import sys

from .profile_commands import profile_main


def main(argv=None):
    parser = argparse.ArgumentParser(description="Human profile shortcut demo")
    parser.add_argument("--installation", required=True)
    parser.add_argument("kind", choices=("memory", "user", "soul"))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    return profile_main(args.kind, args.command, installation=args.installation,
                        stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
