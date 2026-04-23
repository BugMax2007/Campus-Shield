from __future__ import annotations

import json
from pathlib import Path

from .models import (
    ActorDefinition,
    AlertWave,
    AreaTrigger,
    ExitZone,
    GameContent,
    Interaction,
    PropDef,
    RectDef,
    RoomArea,
    Scenario,
    SceneData,
    SceneLink,
    SpawnPoint,
    StoryBeat,
    TermEntry,
    parse_point,
    parse_points,
    parse_string_list,
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_rect(value: object) -> RectDef:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"Invalid rect payload: {value}")
    return RectDef(int(value[0]), int(value[1]), int(value[2]), int(value[3]))


def _collides_with_rects(
    scene_width: int,
    scene_height: int,
    blockers: tuple[RectDef, ...],
    px: float,
    py: float,
    size: int,
) -> bool:
    rect = RectDef(int(px - size / 2), int(py - size / 2), size, size)
    if rect.x < 0 or rect.y < 0 or rect.x + rect.width > scene_width or rect.y + rect.height > scene_height:
        return True
    for blocker in blockers:
        if not (
            rect.x + rect.width <= blocker.x
            or rect.x >= blocker.x + blocker.width
            or rect.y + rect.height <= blocker.y
            or rect.y >= blocker.y + blocker.height
        ):
            return True
    return False


def _spawn_is_navigable(scene: SceneData, spawn: SpawnPoint) -> bool:
    radius = max(14, int(scene.spawn_validation_radius))
    px = spawn.x + spawn.width / 2
    py = spawn.y + spawn.height / 2
    blockers = scene.blockers()
    if _collides_with_rects(scene.width, scene.height, blockers, px, py, radius * 2):
        return False
    step = max(24, radius + 8)
    candidates = ((step, 0), (-step, 0), (0, step), (0, -step))
    open_count = 0
    for dx, dy in candidates:
        if not _collides_with_rects(scene.width, scene.height, blockers, px + dx, py + dy, radius * 2):
            open_count += 1
    return open_count >= 2


def load_content(base_path: Path) -> GameContent:
    scenes, scene_order = load_scenes(base_path / "data" / "maps" / "index.json")
    scenario = load_scenario(base_path / "data" / "scenarios" / "main_scenario.json")
    interactions = load_interactions(base_path / "data" / "interactions.json")
    actors = load_actors(base_path / "data" / "actors.json")
    terms = load_terms(base_path / "data" / "terms.json")
    localizations = {
        "zh-CN": _load_json(base_path / "data" / "localization" / "zh-CN.json"),
        "en-US": _load_json(base_path / "data" / "localization" / "en-US.json"),
    }
    validate_content(scenes, scenario, interactions, actors, terms, localizations)
    return GameContent(
        scenes=scenes,
        scene_order=scene_order,
        interactions=interactions,
        actors=actors,
        terms=terms,
        scenario=scenario,
        localizations=localizations,
    )


def load_scenes(path: Path) -> tuple[dict[str, SceneData], tuple[str, ...]]:
    raw = _load_json(path)
    if not isinstance(raw, dict):
        raise ValueError("Scene graph must be an object.")
    raw_scenes = raw.get("scenes", [])
    scenes: dict[str, SceneData] = {}
    order: list[str] = []
    for scene in raw_scenes:
        scene_id = str(scene["id"])
        order.append(scene_id)
        collisions = tuple(_parse_rect(rect) for rect in scene.get("collisions", []))
        nav_blockers = tuple(_parse_rect(rect) for rect in scene.get("nav_blockers", []))
        rooms = tuple(
            RoomArea(
                id=str(room["id"]),
                label_key=str(room["label_key"]),
                x=int(room["rect"][0]),
                y=int(room["rect"][1]),
                width=int(room["rect"][2]),
                height=int(room["rect"][3]),
            )
            for room in scene.get("rooms", [])
        )
        safe_areas = tuple(
            AreaTrigger(
                id=str(area["id"]),
                label_key=str(area["label_key"]),
                tags=parse_string_list(area.get("tags")),
                x=int(area["rect"][0]),
                y=int(area["rect"][1]),
                width=int(area["rect"][2]),
                height=int(area["rect"][3]),
            )
            for area in scene.get("safe_areas", [])
        )
        risk_areas = tuple(
            AreaTrigger(
                id=str(area["id"]),
                label_key=str(area["label_key"]),
                tags=parse_string_list(area.get("tags")),
                x=int(area["rect"][0]),
                y=int(area["rect"][1]),
                width=int(area["rect"][2]),
                height=int(area["rect"][3]),
            )
            for area in scene.get("risk_areas", [])
        )
        props = tuple(
            PropDef(
                id=str(item["id"]),
                type=str(item.get("type", "prop")),
                label_key=str(item.get("label_key", "")),
                solid=bool(item.get("solid", False)),
                x=int(item["rect"][0]),
                y=int(item["rect"][1]),
                width=int(item["rect"][2]),
                height=int(item["rect"][3]),
            )
            for item in scene.get("props", [])
        )
        exit_zones = tuple(
            ExitZone(
                id=str(item["id"]),
                label_key=str(item["label_key"]),
                action=str(item["action"]),
                trigger_mode=str(item.get("trigger_mode", "press")),
                state_rules=parse_string_list(item.get("state_rules")),
                x=int(item["rect"][0]),
                y=int(item["rect"][1]),
                width=int(item["rect"][2]),
                height=int(item["rect"][3]),
            )
            for item in scene.get("exit_zones", [])
        )
        links = tuple(
            SceneLink(
                id=str(link["id"]),
                label_key=str(link["label_key"]),
                target_scene_id=str(link["target_scene_id"]),
                target_spawn_id=str(link["target_spawn_id"]),
                locked_on_alert=bool(link.get("locked_on_alert", False)),
                x=int(link["rect"][0]),
                y=int(link["rect"][1]),
                width=int(link["rect"][2]),
                height=int(link["rect"][3]),
            )
            for link in scene.get("links", [])
        )
        boards = tuple(
            RectDef(
                x=int(board[0]),
                y=int(board[1]),
                width=int(board[2]),
                height=int(board[3]),
            )
            for board in scene.get("map_boards", [])
        )
        spawns = tuple(
            SpawnPoint(
                id=str(spawn["id"]),
                scene_id=scene_id,
                label_key=str(spawn["label_key"]),
                x=int(spawn["rect"][0]),
                y=int(spawn["rect"][1]),
                width=int(spawn["rect"][2]),
                height=int(spawn["rect"][3]),
            )
            for spawn in scene.get("spawns", [])
        )
        scenes[scene_id] = SceneData(
            id=scene_id,
            building_key=str(scene["building_key"]),
            floor_label_key=str(scene["floor_label_key"]),
            width=int(scene["width"]),
            height=int(scene["height"]),
            theme_color=str(scene.get("theme_color", "#223344")),
            collisions=collisions,
            nav_blockers=nav_blockers,
            spawn_validation_radius=int(scene.get("spawn_validation_radius", 14)),
            rooms=rooms,
            safe_areas=safe_areas,
            risk_areas=risk_areas,
            props=props,
            exit_zones=exit_zones,
            map_boards=boards,
            links=links,
            spawns=spawns,
        )
    return scenes, tuple(order)


def load_interactions(path: Path) -> tuple[Interaction, ...]:
    raw = _load_json(path)
    return tuple(
        Interaction(
            id=str(item["id"]),
            scene_id=str(item["scene_id"]),
            floor_id=str(item.get("floor_id", "unknown")),
            room_id=str(item.get("room_id", "unknown")),
            x=int(item["x"]),
            y=int(item["y"]),
            width=int(item["width"]),
            height=int(item["height"]),
            type=str(item["type"]),
            label_key=str(item["label_key"]),
            icon=str(item.get("icon", "?")),
            state_rules=parse_string_list(item.get("state_rules")),
            education_key=str(item.get("education_key", "")),
            action=str(item["action"]),
            cooldown=float(item.get("cooldown", 0.0)),
            trigger_mode=str(item.get("trigger_mode", "press")),
            trigger_radius=float(item.get("trigger_radius", 85)),
            requires_item=str(item["requires_item"]) if item.get("requires_item") else None,
            unlock_flag=str(item["unlock_flag"]) if item.get("unlock_flag") else None,
            fail_feedback_key=str(item.get("fail_feedback_key")) if item.get("fail_feedback_key") else None,
        )
        for item in raw
    )


def load_actors(path: Path) -> tuple[ActorDefinition, ...]:
    raw = _load_json(path)
    raw_items = raw.get("actors", []) if isinstance(raw, dict) else raw
    return tuple(
        ActorDefinition(
            id=str(item["id"]),
            kind=str(item["kind"]),
            scene_id=str(item["scene_id"]),
            x=int(item["x"]),
            y=int(item["y"]),
            patrol=parse_points(item.get("patrol", [])),
            speed=float(item.get("speed", 90)),
            vision_deg=float(item.get("vision_deg", 70)),
            vision_distance=float(item.get("vision_distance", 320)),
            hearing_radius=float(item.get("hearing_radius", 260)),
            role=str(item.get("role", "patrol")),
            dispatch_role=str(item.get("dispatch_role", item.get("role", "patrol"))),
            can_cross_scene=bool(item.get("can_cross_scene", False)),
            fallback_anchor=parse_point(item.get("fallback_anchor"), default=(int(item["x"]), int(item["y"]))),
            label_key=str(item.get("label_key", "")),
            hint_key=str(item.get("hint_key", "")),
            noise_interval=float(item.get("noise_interval", 0.0)),
            script=str(item.get("script", "")),
        )
        for item in raw_items
    )


def load_scenario(path: Path) -> Scenario:
    raw = _load_json(path)
    opening = tuple(
        StoryBeat(
            title_key=str(item["title_key"]),
            body_key=str(item["body_key"]),
            duration=float(item.get("duration", 8)),
        )
        for item in raw.get("opening_sequence", [])
    )
    waves = tuple(
        AlertWave(
            at=int(item["at"]),
            phase=str(item["phase"]),
            title_key=str(item["title_key"]),
            body_key=str(item["body_key"]),
            incident_scene_id=str(item["incident_scene_id"]),
            blocked_link_ids=parse_string_list(item.get("blocked_link_ids")),
        )
        for item in raw.get("alert_waves", [])
    )
    return Scenario(
        scenario_id=str(raw["scenario_id"]),
        opening_sequence=opening,
        alert_waves=waves,
        ending_conditions=dict(raw.get("ending_conditions", {})),
        clue_chain=parse_string_list(raw.get("clue_chain")),
        safe_room_tags=parse_string_list(raw.get("safe_room_tags")),
        fail_conditions=parse_string_list(raw.get("fail_conditions")),
        debrief_notes=parse_string_list(raw.get("debrief_notes")),
    )


def load_terms(path: Path) -> dict[str, TermEntry]:
    raw = _load_json(path)
    return {
        str(item["id"]): TermEntry(
            id=str(item["id"]),
            title_key=str(item["title_key"]),
            body_key=str(item["body_key"]),
            category=str(item["category"]),
        )
        for item in raw
    }


def validate_content(
    scenes: dict[str, SceneData],
    scenario: Scenario,
    interactions: tuple[Interaction, ...],
    actors: tuple[ActorDefinition, ...],
    terms: dict[str, TermEntry],
    localizations: dict[str, dict[str, str]],
) -> None:
    errors: list[str] = []
    scene_ids = set(scenes.keys())
    spawn_ids = {spawn.id for scene in scenes.values() for spawn in scene.spawns}
    link_ids = {link.id for scene in scenes.values() for link in scene.links}
    interaction_ids = {interaction.id for interaction in interactions}

    if len(scenes) < 5:
        errors.append("Expected at least 5 scenes for phase 1.")
    if "outdoor_main" not in scenes:
        errors.append("Missing required scene: outdoor_main.")

    for scene in scenes.values():
        if not scene.map_boards:
            errors.append(f"Scene {scene.id} must contain at least one map board.")
        if scene.spawn_validation_radius < 10:
            errors.append(f"Scene {scene.id} spawn_validation_radius too small.")
        for link in scene.links:
            if link.target_scene_id not in scene_ids:
                errors.append(f"Link {link.id} points to unknown scene {link.target_scene_id}.")
            if link.target_spawn_id not in spawn_ids:
                errors.append(f"Link {link.id} points to unknown spawn {link.target_spawn_id}.")
        for zone in scene.exit_zones:
            if zone.action not in {"north_exit", "secret_tunnel"}:
                errors.append(f"Exit zone {zone.id} has unsupported action {zone.action}.")
            if zone.trigger_mode not in {"press", "proximity"}:
                errors.append(f"Exit zone {zone.id} has invalid trigger_mode {zone.trigger_mode}.")
        for spawn in scene.spawns:
            if not _spawn_is_navigable(scene, spawn):
                errors.append(f"Spawn {spawn.id} in scene {scene.id} is blocked or not navigable.")

    for interaction in interactions:
        if interaction.scene_id not in scene_ids:
            errors.append(f"Interaction {interaction.id} uses unknown scene {interaction.scene_id}.")
        if interaction.education_key and interaction.education_key not in terms:
            errors.append(f"Interaction {interaction.id} references unknown term {interaction.education_key}.")
        if interaction.unlock_flag and interaction.unlock_flag not in scenario.clue_chain:
            errors.append(f"Interaction {interaction.id} uses unknown unlock flag {interaction.unlock_flag}.")
        if interaction.trigger_mode not in {"press", "proximity"}:
            errors.append(f"Interaction {interaction.id} has invalid trigger_mode {interaction.trigger_mode}.")
        if interaction.trigger_radius < 20:
            errors.append(f"Interaction {interaction.id} trigger_radius is too small.")

    raider_count = 0
    robot_count = 0
    for actor in actors:
        if actor.scene_id not in scene_ids:
            errors.append(f"Actor {actor.id} uses unknown scene {actor.scene_id}.")
        if not actor.patrol:
            errors.append(f"Actor {actor.id} must provide a patrol path.")
        if actor.kind == "raider":
            raider_count += 1
        if actor.kind == "robot":
            robot_count += 1
    if raider_count < 3:
        errors.append("Need at least 3 raiders for phase 1.")
    if robot_count < 2:
        errors.append("Need at least 2 robots for phase 1.")

    for wave in scenario.alert_waves:
        if wave.incident_scene_id not in scene_ids:
            errors.append(f"Alert wave points to unknown scene {wave.incident_scene_id}.")
        for link_id in wave.blocked_link_ids:
            if link_id not in link_ids:
                errors.append(f"Alert wave references unknown blocked link {link_id}.")

    for clue_id in scenario.clue_chain:
        if clue_id not in interaction_ids:
            errors.append(f"Clue chain references unknown interaction {clue_id}.")

    required_keys = {
        "game.title",
        "phase.Explore",
        "phase.Alert",
        "phase.Shelter",
        "phase.AllClear",
        "phase.Debrief",
        "ui.map_access_denied",
        "ui.you_are_here",
        "ui.location",
        "ui.building",
        "ui.floor",
        "ui.room_unknown",
        "ui.throw_bottle",
        "ui.bottle_empty",
        "ui.bottle_pickup",
        "ui.exit_blocked",
        "success.exit_gate",
        "success.secret_tunnel",
        "success.police_arrival",
        "failure.captured",
    } | {term.title_key for term in terms.values()} | {term.body_key for term in terms.values()}

    for scene in scenes.values():
        required_keys.add(scene.building_key)
        required_keys.add(scene.floor_label_key)
        for room in scene.rooms:
            required_keys.add(room.label_key)
        for area in scene.safe_areas:
            required_keys.add(area.label_key)
        for area in scene.risk_areas:
            required_keys.add(area.label_key)
        for link in scene.links:
            required_keys.add(link.label_key)
        for zone in scene.exit_zones:
            required_keys.add(zone.label_key)

    for interaction in interactions:
        required_keys.add(interaction.label_key)
        if interaction.fail_feedback_key:
            required_keys.add(interaction.fail_feedback_key)
    for actor in actors:
        if actor.label_key:
            required_keys.add(actor.label_key)
        if actor.hint_key:
            required_keys.add(actor.hint_key)
    for beat in scenario.opening_sequence:
        required_keys.add(beat.title_key)
        required_keys.add(beat.body_key)
    for wave in scenario.alert_waves:
        required_keys.add(wave.title_key)
        required_keys.add(wave.body_key)
    for note in scenario.debrief_notes:
        required_keys.add(note)

    for language, strings in localizations.items():
        missing = [key for key in sorted(required_keys) if key not in strings]
        if missing:
            errors.append(f"{language} missing keys: {', '.join(missing[:10])}")

    if errors:
        raise ValueError("\n".join(errors))
