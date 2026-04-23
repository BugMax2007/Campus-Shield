#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! python3 -c "import pygame, pytmx" >/dev/null 2>&1; then
  echo "Installing required packages..."
  python3 -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

echo "Launching Campus Safe..."
python3 -m campus_safe_game.main "$@"
