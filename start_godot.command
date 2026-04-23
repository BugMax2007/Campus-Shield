#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GODOT_BIN="/Applications/Godot.app/Contents/MacOS/Godot"

if [[ ! -x "$GODOT_BIN" ]]; then
  echo "Godot was not found at: $GODOT_BIN"
  echo "Install Godot 4.6.2 or update this launcher path."
  exit 1
fi

echo "Launching Campus Shield Godot rebuild..."
"$GODOT_BIN" --path "$SCRIPT_DIR/godot" "$@"
