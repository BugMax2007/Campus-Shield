#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT_BIN="/Applications/Godot.app/Contents/MacOS/Godot"

python3 -m unittest discover -s "$ROOT/tests"
"$GODOT_BIN" --headless --path "$ROOT/godot" --quit
