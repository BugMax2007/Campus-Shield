#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT_BIN="/Applications/Godot.app/Contents/MacOS/Godot"

python3 -m unittest discover -s "$ROOT/tests"
"$GODOT_BIN" --headless --path "$ROOT/godot" --quit
UI_OUTPUT="$("$GODOT_BIN" --headless --path "$ROOT/godot" --script "$ROOT/godot/tools/ui_layout_check.gd" 2>&1 || true)"
printf '%s\n' "$UI_OUTPUT"
grep -q "UI layout check OK" <<< "$UI_OUTPUT"
AI_OUTPUT="$("$GODOT_BIN" --headless --path "$ROOT/godot" --script "$ROOT/godot/tools/ai_behavior_check.gd" 2>&1 || true)"
printf '%s\n' "$AI_OUTPUT"
grep -q "AI behavior check OK" <<< "$AI_OUTPUT"
