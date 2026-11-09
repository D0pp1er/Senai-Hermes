#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
if ! command -v python3 >/dev/null; then
  echo "Install Python 3.10+ first (Ubuntu: sudo apt install python3 python3-venv)."
  exit 1
fi
if ! python3 -m venv .venv; then
  echo "Python venv support is missing."
  read -r -p "Install Ubuntu venv/pip packages using sudo? [y/N]: " answer
  if [[ "$answer" != y && "$answer" != Y ]]; then exit 1; fi
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip check
if ! command -v codex >/dev/null; then
  echo "Codex CLI missing: install using https://developers.openai.com/codex/cli/ and rerun."
  exit 1
fi
.venv/bin/python -m senai setup --root "$repo_root"
echo "Activate this environment with source .venv/bin/activate"
read -r -p "Create ~/.local/bin/senai pointing to this installation? [y/N]: " answer
if [[ "$answer" == y || "$answer" == Y ]]; then
  mkdir -p "$HOME/.local/bin"
  if [[ -e "$HOME/.local/bin/senai" || -L "$HOME/.local/bin/senai" ]]; then
    echo "Existing launcher preserved. Activate this venv instead."
  else
    ln -s "$repo_root/.venv/bin/senai" "$HOME/.local/bin/senai"
    echo 'Ensure ~/.local/bin is in PATH; shell startup files were not changed.'
  fi
fi
echo "Setup complete. No service started."
