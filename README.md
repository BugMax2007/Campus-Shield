# Campus Shield

Campus Shield is a playable bilingual 2D campus safety education game. It is designed as an educational tool for Chinese high-school students preparing to study abroad and focuses on official alerts, safe-space selection, route judgment, and campus support systems. Through game experiences, players learn what they should do in a potential emergency to better protect themselves.

## Current Primary Build

- Godot 4.6 rebuild is the primary development target.
- Chapter 01 focuses on the library and student center as a 10-15 minute narrative stealth education level.
- Data-driven Tiled level with rooms, walls, cover, interactables, patrol paths, exits, signage, robots, and raiders.
- Campus-signage UI style with responsive menu, HUD, phone, map terminal, pause, and debrief screens.
- Playable routes include main exit evacuation, service-route evacuation after clues, and waiting for assistance in a qualified safe space.
- The Python/Pygame version is preserved as a legacy prototype and wording/mechanics reference.

## Run

### Godot Rebuild

The Godot version under `godot/` is now the primary development target. It contains the rebuilt narrative stealth education level and is the version to improve first.

macOS:

```bash
./start_godot.command
```

Manual Godot launch:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot
```

Windows:

```bat
start_godot.bat
```

### Python Prototype

The original Python/Pygame prototype is now a legacy reference build. Keep it for data, wording, and mechanics reference; do not continue major UI or map work there.

### macOS

```bash
./start_game.command
```

### Windows

Open `start_game.bat` by double-clicking it, or run:

```bat
start_game.bat
```

If it does not open on Windows:

```bat
py -3 --version
py -3 -m pip install -r requirements.txt
start_game.bat
```

If the window flashes and closes, open `cmd` in the project folder and run `start_game.bat` there so you can read the error.

### Manual CLI

macOS / Linux:

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m campus_safe_game.main
```

Windows:

```bat
py -3 -m pip install -r requirements.txt
set PYTHONPATH=src
py -3 -m campus_safe_game.main
```

## Controls

- `WASD`: move
- `E`: interact
- `Q`: throw bottle noise distraction
- `Tab`: phone
- `M`: map terminal near in-scene map boards
- `Esc`: pause / resume
- Arrow keys + `Enter`: menu navigation

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Godot rebuild checks:

```bash
./tools/check_godot_rebuild.sh
```

This runs Python data tests, a Godot headless launch, and a Godot UI layout check across `1280x720`, `1600x900`, and `1920x1080`.

## Legacy UI Snapshots

```bash
PYTHONPATH=src SDL_VIDEODRIVER=dummy python3 tools/render_ui_snapshots.py
```

This exports screenshots for the legacy Python prototype into `artifacts/snapshots/`.

## Prototype Notes

- The prototype intentionally avoids graphic violence and does not implement combat.
- Danger is represented through alerts, blocked routes, public-space exposure, and NPC behavior.
- Audio is stubbed out for now; all important cues are text-visible on screen.
