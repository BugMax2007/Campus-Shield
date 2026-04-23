from __future__ import annotations

from dataclasses import dataclass, field

from .models import AreaTrigger


SCORE_LIMITS = {
    "space_choice": 30,
    "official_info": 25,
    "situational_awareness": 20,
    "low_risk_assist": 15,
    "knowledge_collection": 10,
}


ACTION_SCORE_MAP = {
    "map_board": ("situational_awareness", 4),
    "broadcast": ("official_info", 6),
    "phone_sync": ("official_info", 7),
    "safe_room_check": ("space_choice", 6),
    "clue_collect": ("knowledge_collection", 4),
    "bottle_pickup": ("situational_awareness", 3),
    "robot_hint": ("low_risk_assist", 4),
    "north_exit": ("space_choice", 7),
    "secret_tunnel": ("space_choice", 7),
}


OBJECTIVE_CHECKLISTS = {
    "Explore": (
        ("check.opening_map_board", lambda d: d["map_reads"] >= 1),
        ("check.opening_stairs", lambda d: d["floor_changes"] >= 1),
    ),
    "Alert": (
        ("check.alert_read_update", lambda d: not d["unread_alert"]),
        ("check.alert_collect_clue", lambda d: d["clues"] >= 1),
        ("check.alert_use_bottle", lambda d: d["bottle_throws"] >= 1),
    ),
    "Shelter": (
        ("check.shelter_find_safe_room", lambda d: d["safe_seconds"] >= 8),
        ("check.shelter_avoid_capture", lambda d: not d["captured"]),
        ("check.shelter_confirm_route", lambda d: d["clues"] >= 3 or d["exit_attempts"] >= 1),
    ),
    "AllClear": (("check.all_clear_resolve", lambda d: True),),
    "Debrief": (("check.all_clear_resolve", lambda d: True),),
}


@dataclass
class ScoreCard:
    values: dict[str, int] = field(default_factory=lambda: {name: 0 for name in SCORE_LIMITS})

    def add(self, category: str, amount: int) -> None:
        if category not in self.values:
            return
        self.values[category] = min(SCORE_LIMITS[category], self.values[category] + amount)

    def total(self) -> int:
        return sum(self.values.values())


def phase_allows(current_phase: str, state_rules: tuple[str, ...]) -> bool:
    if not state_rules:
        return True
    return current_phase in state_rules or "Always" in state_rules


def qualifies_safe_area(trigger: AreaTrigger, required_tags: tuple[str, ...]) -> bool:
    return set(required_tags).issubset(set(trigger.tags))


def build_objective_checklist(
    phase: str,
    *,
    unread_alert: bool,
    map_reads: int,
    floor_changes: int,
    clues: int,
    bottle_throws: int,
    safe_seconds: float,
    captured: bool,
    exit_attempts: int,
) -> list[tuple[str, bool]]:
    data = {
        "unread_alert": unread_alert,
        "map_reads": map_reads,
        "floor_changes": floor_changes,
        "clues": clues,
        "bottle_throws": bottle_throws,
        "safe_seconds": safe_seconds,
        "captured": captured,
        "exit_attempts": exit_attempts,
    }
    return [(key, bool(fn(data))) for key, fn in OBJECTIVE_CHECKLISTS.get(phase, ())]


def build_debrief_feedback_keys(
    *,
    ending: str,
    captured: bool,
    clues: int,
    bottle_throws: int,
    alerts_ignored: int,
    safe_seconds: float,
) -> list[str]:
    keys = [f"feedback.ending.{ending}"]
    keys.append("feedback.capture.bad" if captured else "feedback.capture.good")
    keys.append("feedback.clue.good" if clues >= 3 else "feedback.clue.bad")
    keys.append("feedback.bottle.good" if bottle_throws >= 1 else "feedback.bottle.bad")
    keys.append("feedback.alert.good" if alerts_ignored == 0 else "feedback.alert.bad")
    keys.append("feedback.safe.good" if safe_seconds >= 20 else "feedback.safe.bad")
    return keys
