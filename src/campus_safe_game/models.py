from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RectDef:
    x: int
    y: int
    width: int
    height: int

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)


@dataclass(frozen=True)
class RoomArea(RectDef):
    id: str
    label_key: str


@dataclass(frozen=True)
class AreaTrigger(RectDef):
    id: str
    label_key: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PropDef(RectDef):
    id: str
    type: str
    label_key: str = ""
    solid: bool = False


@dataclass(frozen=True)
class ExitZone(RectDef):
    id: str
    label_key: str
    action: str
    trigger_mode: str = "press"
    state_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneLink(RectDef):
    id: str
    label_key: str
    target_scene_id: str
    target_spawn_id: str
    locked_on_alert: bool = False


@dataclass(frozen=True)
class SpawnPoint(RectDef):
    id: str
    scene_id: str
    label_key: str


@dataclass(frozen=True)
class SceneData:
    id: str
    building_key: str
    floor_label_key: str
    width: int
    height: int
    theme_color: str
    collisions: tuple[RectDef, ...]
    nav_blockers: tuple[RectDef, ...]
    spawn_validation_radius: int
    rooms: tuple[RoomArea, ...]
    safe_areas: tuple[AreaTrigger, ...]
    risk_areas: tuple[AreaTrigger, ...]
    props: tuple[PropDef, ...]
    exit_zones: tuple[ExitZone, ...]
    map_boards: tuple[RectDef, ...]
    links: tuple[SceneLink, ...]
    spawns: tuple[SpawnPoint, ...]

    def room_at(self, px: float, py: float) -> RoomArea | None:
        for room in self.rooms:
            if room.contains(px, py):
                return room
        return None

    def safe_area_at(self, px: float, py: float) -> AreaTrigger | None:
        for area in self.safe_areas:
            if area.contains(px, py):
                return area
        return None

    def risk_area_at(self, px: float, py: float) -> AreaTrigger | None:
        for area in self.risk_areas:
            if area.contains(px, py):
                return area
        return None

    def link_at(self, px: float, py: float) -> SceneLink | None:
        for link in self.links:
            if link.contains(px, py):
                return link
        return None

    def exit_zone_at(self, px: float, py: float) -> ExitZone | None:
        for zone in self.exit_zones:
            if zone.contains(px, py):
                return zone
        return None

    def blockers(self) -> tuple[RectDef, ...]:
        base = self.nav_blockers if self.nav_blockers else self.collisions
        solids = [
            RectDef(item.x, item.y, item.width, item.height)
            for item in self.props
            if item.solid
        ]
        return tuple(list(base) + solids)

    def nearest_board(self, px: float, py: float, max_distance: float = 90) -> RectDef | None:
        nearest: RectDef | None = None
        nearest_distance = max_distance
        for board in self.map_boards:
            cx, cy = board.center()
            distance = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
            if distance <= nearest_distance:
                nearest_distance = distance
                nearest = board
        return nearest

    def spawn_by_id(self, spawn_id: str) -> SpawnPoint | None:
        for spawn in self.spawns:
            if spawn.id == spawn_id:
                return spawn
        return None


@dataclass(frozen=True)
class Interaction(RectDef):
    id: str
    scene_id: str
    floor_id: str
    room_id: str
    type: str
    label_key: str
    icon: str
    state_rules: tuple[str, ...]
    education_key: str
    action: str
    cooldown: float
    trigger_mode: str = "press"
    trigger_radius: float = 85.0
    requires_item: str | None = None
    unlock_flag: str | None = None
    fail_feedback_key: str | None = None


@dataclass(frozen=True)
class ActorDefinition:
    id: str
    kind: str
    scene_id: str
    x: int
    y: int
    patrol: tuple[tuple[int, int], ...]
    speed: float
    vision_deg: float = 70.0
    vision_distance: float = 320.0
    hearing_radius: float = 260.0
    role: str = "patrol"
    dispatch_role: str = "patrol"
    can_cross_scene: bool = False
    fallback_anchor: tuple[int, int] = (0, 0)
    label_key: str = ""
    hint_key: str = ""
    noise_interval: float = 0.0
    script: str = ""


@dataclass(frozen=True)
class TermEntry:
    id: str
    title_key: str
    body_key: str
    category: str


@dataclass(frozen=True)
class StoryBeat:
    title_key: str
    body_key: str
    duration: float


@dataclass(frozen=True)
class AlertWave:
    at: int
    phase: str
    title_key: str
    body_key: str
    incident_scene_id: str
    blocked_link_ids: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    opening_sequence: tuple[StoryBeat, ...]
    alert_waves: tuple[AlertWave, ...]
    ending_conditions: dict[str, Any]
    clue_chain: tuple[str, ...]
    safe_room_tags: tuple[str, ...]
    fail_conditions: tuple[str, ...]
    debrief_notes: tuple[str, ...]


@dataclass(frozen=True)
class GameContent:
    scenes: dict[str, SceneData]
    scene_order: tuple[str, ...]
    interactions: tuple[Interaction, ...]
    actors: tuple[ActorDefinition, ...]
    terms: dict[str, TermEntry]
    scenario: Scenario
    localizations: dict[str, dict[str, str]]

    def scene_by_id(self, scene_id: str) -> SceneData | None:
        return self.scenes.get(scene_id)


@dataclass
class SaveState:
    language: str = "zh-CN"
    completed_runs: int = 0
    best_score: int = 0
    unlocked_terms: list[str] = field(default_factory=list)
    accessibility_settings: dict[str, Any] = field(
        default_factory=lambda: {"subtitles": True, "high_contrast": False}
    )
    current_scene: str = "outdoor_main"
    current_floor: str = "outdoor"
    inventory: list[str] = field(default_factory=list)
    clues_found: list[str] = field(default_factory=list)
    ending_history: list[str] = field(default_factory=list)
    difficulty: str = "normal"


def parse_string_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    return ()


def parse_points(value: Any) -> tuple[tuple[int, int], ...]:
    if not isinstance(value, list):
        return ()
    points: list[tuple[int, int]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            continue
        points.append((int(item[0]), int(item[1])))
    return tuple(points)


def parse_point(value: Any, *, default: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    if isinstance(value, list) and len(value) == 2:
        return (int(value[0]), int(value[1]))
    return default
