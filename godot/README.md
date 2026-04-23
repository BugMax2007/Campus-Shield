# Campus Shield Godot Rebuild

This folder contains the next-generation Godot 4 rebuild of Campus Shield.

The existing Python/Pygame version remains in the repository as a playable prototype and reference implementation. The Godot version is the intended path for major improvements to UI, map design, AI readability, animation, export, and production-quality game feel.

## Current Chapter 01 Rebuild

- Data-driven Tiled level: `data/levels/chapter_01.tmx` exported to `chapter_01.json`
- Responsive campus-signage UI using Godot Control nodes
- Menu, opening, HUD, phone, map terminal, pause, and debrief screens
- Top-down playable world
- Room labels, safe/risk room coloring, visible bookshelves/tables, map boards, exits, clue pickups
- Player movement with collision
- Raider patrol, vision cone, hearing/noise investigation, global investigation broadcast, chase/search states
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
- Add authored classroom/library prop variants and stronger room dressing.
- Add authored animations and sound cues.
- Add stronger route tutorials for main exit, service route, and waiting for assistance.

## Verification

```bash
../tools/check_godot_rebuild.sh
```

The check covers Python data tests, Godot headless startup, and responsive UI layout validation for menu, gameplay, alert, phone, map, pause, and debrief screens at `1280x720`, `1600x900`, and `1920x1080`.
