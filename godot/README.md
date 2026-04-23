# Campus Shield Godot Rebuild

This folder contains the next-generation Godot 4 rebuild of Campus Shield.

The existing Python/Pygame version remains in the repository as a playable prototype and reference implementation. The Godot version is the intended path for major improvements to UI, map design, AI readability, animation, export, and production-quality game feel.

## Current Vertical Slice

- Main menu and opening card
- Top-down playable world
- Room labels, safe/risk room coloring, obstacles, map boards, exits, clue pickups
- Player movement with collision
- Raider patrol, vision cone, hearing/noise investigation, chase/search states
- Robot hints
- Bottle distraction with `Q`
- Map terminal with `M` near a map board
- Phone panel with `Tab`
- Pause with `Esc`
- Debrief endings for main exit, service tunnel, waiting for assistance, and capture

## Run

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot
```

Or open Godot and import this folder as a project.

## Next Build Targets

- Replace programmatic blockout with Tiled/LDtk-authored levels.
- Split entities into reusable scenes: player, raider, robot, map terminal, interactable, room trigger.
- Add a full UI theme using Godot `Control` nodes rather than only drawing overlays.
- Add authored animations and sound cues.
- Add export presets for macOS and Windows.
