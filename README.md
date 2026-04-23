# Campus Shield

Campus Shield is a playable bilingual 2D campus safety education game. It is designed as an educational tool for Chinese high-school students preparing to study abroad and focuses on official alerts, safe-space selection, route judgment, and campus support systems. Through game experiences, players learn what they should do in a potential emergency to better protect themselves.

## Features

- Top-down 2D campus with 6 zones and 3 spawn points.
- `Story` and `Practice` modes on the same map.
- Data-driven `.tmx` world, scenario timeline, interactions, NPCs, terms, and localization.
- Bilingual UI with Chinese primary copy and English secondary copy.
- Debrief scoring across space choice, official information use, situational awareness, low-risk assistance, and knowledge collection.
- Save file for language, unlocked terms, best score, completed runs, and accessibility settings.

## Run

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
- `Tab`: phone + glossary
- `M`: campus map
- `Esc`: pause / resume
- Arrow keys + `Enter`: menu navigation

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## UI Snapshots

```bash
PYTHONPATH=src SDL_VIDEODRIVER=dummy python3 tools/render_ui_snapshots.py
```

This exports menu, notice, gameplay, map, phone, pause, and debrief screenshots for `1280x720`, `1600x900`, and `1920x1080` into `artifacts/snapshots/`.

## Prototype Notes

- The prototype intentionally avoids graphic violence and does not implement combat.
- Danger is represented through alerts, blocked routes, public-space exposure, and NPC behavior.
- Audio is stubbed out for now; all important cues are text-visible on screen.
