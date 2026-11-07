"""One-shot Codex CLI wrapper for writing and editing code."""

import argparse
import sys
from pathlib import Path

from .codex import run_codex
from .options import CodexOptions
from .prompts import build_prompt
from .workspace import prepare_workspace


def main(argv=None, stdout=None, stderr=None):
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', help='Code to write or edit (quote the request).')
    parser.add_argument('--project', default='.', help='Target project directory (default: current).')
    parser.add_argument('-m', '--model', help='Codex model override.')
    parser.add_argument('-p', '--profile', help='Codex configuration profile.')
    parser.add_argument('-c', '--config', action='append', default=[], metavar='KEY=VALUE', help='Repeatable Codex configuration override.')
    parser.add_argument('-i', '--image', action='append', default=[], metavar='FILE', help='Attach an image (repeatable).')
    parser.add_argument('--search', action='store_true', help='Enable live Codex web search.')
    args = parser.parse_args(argv)
    try:
        prompt = build_prompt(args.request)
        images = tuple(str(Path(image).expanduser().resolve()) for image in args.image)
        for image in images:
            if not Path(image).is_file():
                raise ValueError(f'Image must be an existing file: {image}')
        workspace = prepare_workspace(args.project)
        options = CodexOptions(model=args.model, profile=args.profile, config=tuple(args.config), images=images, search=args.search)
        response = run_codex(prompt, workspace, options=options)
        print(response, file=stdout)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'senai: {exc}', file=stderr)
        return 2
    except KeyboardInterrupt:
        print('senai: Interrupted.', file=stderr)
        return 130
