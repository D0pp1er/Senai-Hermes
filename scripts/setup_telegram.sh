#!/usr/bin/env bash
set -euo pipefail
# Run from the project to control, or pass --project explicitly.
# The Python wizard prompts privately, pairs an account, saves config, then starts.
exec python3 -m senai telegram --configure --start "$@"
