# Campus Shield Godot Rebuild

This folder contains the next-generation Godot 4 rebuild of Campus Shield.

The existing Python/Pygame version remains in the repository as a playable prototype and reference implementation. The Godot version is the intended path for major improvements to UI, map design, AI readability, animation, export, and production-quality game feel.

## Current Chapter 01 Rebuild

- Data-driven Tiled level: `data/levels/chapter_01.tmx` exported to `chapter_01.json`
- Main menu and opening card using Godot Control UI
- Top-down playable world
- Room labels, safe/risk room coloring, obstacles, map boards, exits, clue pickups
- Player movement with collision
- Raider patrol, vision cone, hearing/noise investigation, chase/search states
- Robot hints
- Bottle distraction with `Q`
- Map terminal with `M` near a map board, backed by level data
- Phone panel with `Tab`
- Pause with `Esc`
- Debrief endings for main exit, service tunnel, waiting for assistance, and capture

## Run

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot
```

Or open Godot and import this folder as a project.

## Level Export

Edit `data/levels/chapter_01.tmx` in Tiled, then regenerate the runtime JSON:

```bash
python3 ../tools/export_tiled_level.py data/levels/chapter_01.tmx data/levels/chapter_01.json
```

## Next Build Targets

- Convert current script-instantiated entities into reusable `.tscn` scenes where visual iteration matters.
- Add a full UI theme using Godot `Control` nodes rather than only drawing overlays.
- Add authored animations and sound cues.
- Add export presets for macOS and Windows.
