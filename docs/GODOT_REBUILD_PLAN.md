# Campus Shield Godot Rebuild Plan

## Goal

Move Campus Shield from a Python prototype into a production-oriented Godot 4 game while preserving the educational goal: through game experiences, players learn what to do in a potential emergency to better protect themselves.

## Why Godot

- Stronger 2D scene workflow than raw Pygame.
- Real UI system for menus, HUD, modals, focus, animation, and resolution scaling.
- Better level authoring with Tiled/LDtk import paths.
- Easier export to macOS and Windows.
- Cleaner entity composition for player, raider AI, robots, interactables, and exits.

## Phase 1: Vertical Slice Foundation

- Add a Godot project under `godot/`.
- Build a playable blockout with movement, collision, map boards, clue pickups, raider patrol/chase, bottle distraction, robots, HUD, phone, pause, and debrief.
- Validate Godot can open the project headlessly.

## Phase 2: Real Level Pipeline

- Author the first polished level in Tiled or LDtk.
- Define layer contracts: floor, walls, cover, room triggers, patrol paths, interactables, spawn points, exits.
- Write an importer or conversion script if needed.

## Phase 3: UI Redesign

- Replace drawn overlays with Godot `Control` scenes.
- Create a campus signage theme: menu, phone, map terminal, pause, fail/success debrief.
- Add keyboard and controller focus states.

## Phase 4: Gameplay Depth

- Raider AI: patrol, investigate noise, chase, search, return, cross-room pressure.
- Robot AI: guide, warning, distraction timing, route hint.
- Multiple endings: guarded main exit, secret service route, wait for assistance.

## Phase 5: Art, Audio, Export

- Build tiles, icons, and character sprites with Pixelorama.
- Process audio cues with Audacity.
- Optional Blender reference renders for room layout and signage.
- Configure macOS and Windows export presets.
