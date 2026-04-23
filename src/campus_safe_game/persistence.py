from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import SaveState


class SaveManager:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> SaveState:
        if not self.path.exists():
            return SaveState()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return SaveState(
            language=data.get("language", "zh-CN"),
            completed_runs=int(data.get("completed_runs", 0)),
            best_score=int(data.get("best_score", 0)),
            unlocked_terms=list(data.get("unlocked_terms", [])),
            accessibility_settings=dict(data.get("accessibility_settings", {"subtitles": True, "high_contrast": False})),
            current_scene=str(data.get("current_scene", "outdoor_main")),
            current_floor=str(data.get("current_floor", "outdoor")),
            inventory=list(data.get("inventory", [])),
            clues_found=list(data.get("clues_found", [])),
            ending_history=list(data.get("ending_history", [])),
            difficulty=str(data.get("difficulty", "normal")),
        )

    def save(self, state: SaveState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False), encoding="utf-8")
