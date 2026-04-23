from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from heapq import heappop, heappush
from pathlib import Path
from typing import Any

import pygame

from .advisor import AdvisoryDecision, CampusAdvisor
from .layout import build_layout, build_screen_layout, split_columns, stack_rows
from .loader import load_content
from .localization import Localizer
from .models import ActorDefinition, ExitZone, GameContent, Interaction, SaveState, SceneData, SceneLink, SpawnPoint
from .persistence import SaveManager
from .rules import (
    ACTION_SCORE_MAP,
    SCORE_LIMITS,
    ScoreCard,
    build_debrief_feedback_keys,
    build_objective_checklist,
    phase_allows,
    qualifies_safe_area,
)
from .ui_theme import UITheme, build_theme


@dataclass
class AppConfig:
    mode: str = "story"
    language: str = "zh-CN"
    spawn_id: str = "random"
    resolution: tuple[int, int] = (1600, 900)
    fullscreen: bool = False


@dataclass
class NoiseEvent:
    scene_id: str
    x: float
    y: float
    timer: float


@dataclass
class ActorRuntime:
    id: str
    kind: str
    scene_id: str
    x: float
    y: float
    state: str = "Patrol"
    path_index: int = 0
    target_x: float = 0.0
    target_y: float = 0.0
    search_timer: float = 0.0
    lost_timer: float = 0.0
    heading_x: float = 1.0
    heading_y: float = 0.0
    noise_timer: float = 0.0
    hint_used: bool = False
    guard_leave_timer: float = 0.0
    route_points: list[tuple[float, float]] = field(default_factory=list)
    route_index: int = 0
    route_recalc_timer: float = 0.0
    search_origin_x: float = 0.0
    search_origin_y: float = 0.0
    search_step: int = 0
    hint_cooldown: float = 0.0
    alert_meter: float = 0.0

    def position(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class SessionState:
    mode: str
    spawn_id: str
    scene_id: str
    player_x: float
    player_y: float
    phase: str = "Explore"
    elapsed: float = 0.0
    alert_elapsed: float = 0.0
    current_wave_index: int = -1
    blocked_links: set[str] = field(default_factory=set)
    interactions_used: set[str] = field(default_factory=set)
    unlocked_terms: set[str] = field(default_factory=set)
    clues_found: set[str] = field(default_factory=set)
    score: ScoreCard = field(default_factory=ScoreCard)
    subtitles: list[tuple[str, str]] = field(default_factory=list)
    message_history: list[tuple[str, str, str]] = field(default_factory=list)
    alert_history: list[tuple[str, str]] = field(default_factory=list)
    current_room_id: str = ""
    unread_alert: bool = False
    ignored_alerts: int = 0
    safe_seconds: float = 0.0
    exposure_seconds: float = 0.0
    reverse_risk_seconds: float = 0.0
    map_reads: int = 0
    floor_changes: int = 0
    bottle_throws: int = 0
    exit_attempts: int = 0
    captured: bool = False
    bottles: int = 3
    inventory: set[str] = field(default_factory=set)
    outcome: str | None = None
    outcome_key: str | None = None
    ending_type: str = "none"
    phone_open: bool = False
    map_open: bool = False
    log_open: bool = False
    log_scroll: int = 0
    paused: bool = False
    pause_selection: int = 0
    opening_active: bool = True
    opening_index: int = 0
    opening_timer: float = 0.0
    completion_saved: bool = False
    last_dir_x: float = 0.0
    last_dir_y: float = -1.0
    global_chase_active: bool = False
    global_chase_timer: float = 0.0
    last_seen_scene_id: str = ""
    last_seen_x: float = 0.0
    last_seen_y: float = 0.0
    last_seen_timer: float = 0.0

    def push_subtitle(self, title: str, body: str) -> None:
        if self.subtitles and self.subtitles[-1] == (title, body):
            return
        self.subtitles.append((title, body))
        del self.subtitles[:-5]


class CampusSafeGame:
    def __init__(self, base_path: Path, config: AppConfig) -> None:
        pygame.init()
        pygame.display.set_caption("Campus Shield")
        self.base_path = base_path
        self.config = config
        self.fullscreen = config.fullscreen
        self.windowed_resolution = config.resolution
        self.screen = self._apply_display_mode()
        self.clock = pygame.time.Clock()
        self.content = load_content(base_path)
        self.save_manager = SaveManager(base_path / "save" / "savegame.json")
        self.save_state = self.save_manager.load()
        if config.language:
            self.save_state.language = config.language
        self.localizer = Localizer(self.content.localizations, self.save_state.language)
        self.ui_theme = self._load_theme()
        self.fonts = self._build_fonts()
        self.advisor = CampusAdvisor(base_path)
        self.running = True
        self.view = "menu"
        self.menu_options = ["start", "mode", "language", "spawn", "quit"]
        self.menu_index = 0
        self.selected_mode = config.mode
        self.selected_language = self.save_state.language
        self.selected_spawn = config.spawn_id
        self.spawn_options = self._build_spawn_options()
        if self.selected_spawn not in self.spawn_options:
            self.selected_spawn = self.spawn_options[0]
        self.session: SessionState | None = None
        self.actor_defs: dict[str, ActorDefinition] = {actor.id: actor for actor in self.content.actors}
        self.actor_states: dict[str, ActorRuntime] = {}
        self.noises: list[NoiseEvent] = []
        self.pause_hint_lines = [
            ("ui.setting_language", "L"),
            ("ui.setting_subtitles", "T"),
            ("ui.setting_high_contrast", "H"),
            ("ui.setting_fullscreen", "F11"),
            ("ui.setting_log", "J"),
        ]
        self.pause_buttons: list[tuple[pygame.Rect, str]] = []
        self.scene_graph = self._build_scene_graph()
        self.scene_nav_graphs = self._build_scene_nav_graphs()
        self._advisory_cache_key: tuple[Any, ...] | None = None
        self._advisory_cache: AdvisoryDecision | None = None

    def _build_spawn_options(self) -> list[str]:
        options = ["random"]
        for scene_id in self.content.scene_order:
            scene = self.content.scenes[scene_id]
            for spawn in scene.spawns:
                if scene_id != "outdoor_main":
                    options.append(spawn.id)
        return options

    def _build_scene_graph(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {scene_id: set() for scene_id in self.content.scene_order}
        for scene in self.content.scenes.values():
            for link in scene.links:
                graph.setdefault(scene.id, set()).add(link.target_scene_id)
        return graph

    def _scene_nav_samples(self, scene: SceneData) -> list[tuple[float, float]]:
        samples: list[tuple[float, float]] = []

        def add_point(x: float, y: float) -> None:
            point = (float(x), float(y))
            if self._collides(scene, point[0], point[1], size=26):
                return
            if any(self._distance(point, existing) < 26 for existing in samples):
                return
            samples.append(point)

        inset = 72
        for room in scene.rooms:
            add_point(room.x + room.width / 2, room.y + room.height / 2)
            add_point(room.x + inset, room.y + room.height / 2)
            add_point(room.x + room.width - inset, room.y + room.height / 2)
            add_point(room.x + room.width / 2, room.y + inset)
            add_point(room.x + room.width / 2, room.y + room.height - inset)
        for board in scene.map_boards:
            cx, cy = board.center()
            add_point(cx, cy)
        for link in scene.links:
            cx, cy = link.center()
            add_point(cx, cy)
        for spawn in scene.spawns:
            add_point(spawn.x + spawn.width / 2, spawn.y + spawn.height / 2)
        for actor in self.content.actors:
            if actor.scene_id != scene.id:
                continue
            for px, py in actor.patrol:
                add_point(px, py)
        corner_offset = 54
        for blocker in scene.nav_blockers:
            touches_outer = (
                (blocker.x <= 40 and blocker.width >= scene.width * 0.5)
                or (blocker.y <= 40 and blocker.height >= scene.height * 0.5)
                or (blocker.x + blocker.width >= scene.width - 40 and blocker.width >= scene.width * 0.5)
                or (blocker.y + blocker.height >= scene.height - 40 and blocker.height >= scene.height * 0.5)
            )
            if touches_outer:
                continue
            corners = (
                (blocker.x - corner_offset, blocker.y - corner_offset),
                (blocker.x + blocker.width + corner_offset, blocker.y - corner_offset),
                (blocker.x - corner_offset, blocker.y + blocker.height + corner_offset),
                (blocker.x + blocker.width + corner_offset, blocker.y + blocker.height + corner_offset),
            )
            for px, py in corners:
                add_point(max(48, min(scene.width - 48, px)), max(48, min(scene.height - 48, py)))
        return samples

    def _build_scene_nav_graphs(self) -> dict[str, dict[str, object]]:
        graphs: dict[str, dict[str, object]] = {}
        for scene_id, scene in self.content.scenes.items():
            points = self._scene_nav_samples(scene)
            adjacency: dict[int, list[tuple[int, float]]] = {index: [] for index in range(len(points))}
            for index, source in enumerate(points):
                for other in range(index + 1, len(points)):
                    target = points[other]
                    distance = self._distance(source, target)
                    if distance > 1100:
                        continue
                    if not self._has_clear_line(scene, source, target):
                        continue
                    adjacency[index].append((other, distance))
                    adjacency[other].append((index, distance))
            graphs[scene_id] = {"points": points, "adjacency": adjacency}
        return graphs

    def _build_fonts(self) -> dict[str, pygame.font.Font]:
        return {
            "display": self.ui_theme.fonts.display,
            "title": self.ui_theme.fonts.title,
            "heading": self.ui_theme.fonts.heading,
            "body": self.ui_theme.fonts.body,
            "small": self.ui_theme.fonts.small,
            "tiny": self.ui_theme.fonts.tiny,
            "mono": self.ui_theme.fonts.mono,
        }

    def _apply_display_mode(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(self.windowed_resolution, pygame.RESIZABLE)

    def _load_theme(self) -> UITheme:
        return build_theme(self.base_path, self.screen.get_size(), self._high_contrast_enabled())

    def _refresh_theme(self) -> None:
        self.ui_theme = self._load_theme()
        self.fonts = self._build_fonts()

    def _all_spawns(self) -> list[SpawnPoint]:
        spawns: list[SpawnPoint] = []
        for scene in self.content.scenes.values():
            spawns.extend(scene.spawns)
        return spawns

    def _spawn_center(self, spawn: SpawnPoint) -> tuple[float, float]:
        return (spawn.x + spawn.width / 2, spawn.y + spawn.height / 2)

    def _spawn_is_valid(self, spawn: SpawnPoint) -> bool:
        scene = self.content.scene_by_id(spawn.scene_id)
        if scene is None:
            return False
        px, py = self._spawn_center(spawn)
        size = max(20, scene.spawn_validation_radius * 2)
        if self._collides(scene, px, py, size=size):
            return False
        step = max(24, scene.spawn_validation_radius + 8)
        open_count = 0
        for dx, dy in ((step, 0), (-step, 0), (0, step), (0, -step)):
            if not self._collides(scene, px + dx, py + dy, size=size):
                open_count += 1
        return open_count >= 2

    def _find_spawn(self, spawn_id: str) -> SpawnPoint | None:
        for spawn in self._all_spawns():
            if spawn.id == spawn_id:
                return spawn
        return None

    def _pick_spawn(self, selected_spawn: str) -> SpawnPoint:
        if selected_spawn != "random":
            explicit = self._find_spawn(selected_spawn)
            if explicit and explicit.scene_id != "outdoor_main" and self._spawn_is_valid(explicit):
                return explicit
        indoor_spawns = [
            spawn
            for spawn in self._all_spawns()
            if spawn.scene_id != "outdoor_main" and self._spawn_is_valid(spawn)
        ]
        if indoor_spawns:
            return random.choice(indoor_spawns)
        any_valid = [spawn for spawn in self._all_spawns() if self._spawn_is_valid(spawn)]
        if any_valid:
            return random.choice(any_valid)
        raise ValueError("No navigable spawn points found.")

    def start_session(self) -> None:
        spawn = self._pick_spawn(self.selected_spawn)
        self.localizer.set_language(self.selected_language)
        self.save_state.language = self.selected_language
        self.session = SessionState(
            mode=self.selected_mode,
            spawn_id=spawn.id,
            scene_id=spawn.scene_id,
            player_x=spawn.x + spawn.width / 2,
            player_y=spawn.y + spawn.height / 2,
            unlocked_terms=set(self.save_state.unlocked_terms),
            clues_found=set(self.save_state.clues_found),
            inventory=set(self.save_state.inventory),
            bottles=3,
        )
        opening = self.content.scenario.opening_sequence
        if opening:
            self.session.opening_timer = opening[0].duration
        else:
            self.session.opening_active = False
        self.actor_states = {}
        for actor in self.content.actors:
            patrol = actor.patrol if actor.patrol else ((actor.x, actor.y),)
            first = patrol[0]
            self.actor_states[actor.id] = ActorRuntime(
                id=actor.id,
                kind=actor.kind,
                scene_id=actor.scene_id,
                x=float(first[0]),
                y=float(first[1]),
                target_x=float(first[0]),
                target_y=float(first[1]),
                heading_x=1.0,
                heading_y=0.0,
                noise_timer=actor.noise_interval,
            )
        self.noises = []
        self._advisory_cache_key = None
        self._advisory_cache = None
        self.view = "play"
        self._update_room_tracking()
        self._post_message("system", "game.title", "objective.explore")

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000
            self._handle_events()
            if self.view == "play" and self.session:
                self._update_play(dt)
            self._render()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_resolution = (max(1280, event.w), max(720, event.h))
                self.screen = self._apply_display_mode()
                self._refresh_theme()
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11 or (
                    event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and event.mod & pygame.KMOD_ALT
                ):
                    self._toggle_fullscreen()
                    continue
                if self.view == "menu":
                    self._handle_menu_key(event.key)
                elif self.view == "play":
                    self._handle_play_key(event.key)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.view == "play":
                self._handle_play_click(event.pos)

    def _handle_menu_key(self, key: int) -> None:
        if key == pygame.K_UP:
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif key == pygame.K_DOWN:
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            direction = -1 if key == pygame.K_LEFT else 1
            field = self.menu_options[self.menu_index]
            if field == "mode":
                self.selected_mode = "practice" if self.selected_mode == "story" else "story"
            elif field == "language":
                self.selected_language = "en-US" if self.selected_language == "zh-CN" else "zh-CN"
            elif field == "spawn":
                index = self.spawn_options.index(self.selected_spawn)
                self.selected_spawn = self.spawn_options[(index + direction) % len(self.spawn_options)]
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            field = self.menu_options[self.menu_index]
            if field == "start":
                self.start_session()
            elif field == "quit":
                self.running = False

    def _handle_play_key(self, key: int) -> None:
        session = self.session
        if session is None:
            return
        if session.outcome:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.view = "menu"
            elif key == pygame.K_r:
                self.start_session()
            return
        if session.opening_active:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._next_opening_beat()
            elif key == pygame.K_s:
                self._skip_opening()
            elif key == pygame.K_ESCAPE:
                self.view = "menu"
            return
        if key == pygame.K_ESCAPE:
            if session.phone_open or session.map_open or session.log_open:
                self._close_overlay_panels()
                return
            session.paused = not session.paused
            if session.paused:
                session.pause_selection = 0
            self._close_overlay_panels()
            return
        if session.paused:
            if key == pygame.K_UP:
                session.pause_selection = (session.pause_selection - 1) % 3
                return
            if key == pygame.K_DOWN:
                session.pause_selection = (session.pause_selection + 1) % 3
                return
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._activate_pause_action(session.pause_selection)
                return
            if key == pygame.K_l:
                self._toggle_language()
            elif key == pygame.K_t:
                self._toggle_accessibility("subtitles")
            elif key == pygame.K_h:
                self._toggle_accessibility("high_contrast")
            return
        if session.log_open:
            if key == pygame.K_UP:
                session.log_scroll = min(session.log_scroll + 1, max(0, len(session.message_history) - 1))
            elif key == pygame.K_DOWN:
                session.log_scroll = max(session.log_scroll - 1, 0)
            elif key == pygame.K_PAGEUP:
                session.log_scroll = min(session.log_scroll + 4, max(0, len(session.message_history) - 1))
            elif key == pygame.K_PAGEDOWN:
                session.log_scroll = max(session.log_scroll - 4, 0)
            elif key in (pygame.K_j, pygame.K_ESCAPE):
                session.log_open = False
            return
        if key == pygame.K_TAB:
            session.phone_open = not session.phone_open
            session.map_open = False
            session.log_open = False
            if session.phone_open:
                self._acknowledge_alert()
            return
        if key == pygame.K_m:
            if session.map_open:
                session.map_open = False
            elif self._can_open_map():
                session.map_open = True
                session.map_reads += 1
                self._score_action("map_board")
            else:
                self._post_message("system", "ui.map_access_denied", "ui.map_access_hint")
            session.phone_open = False
            session.log_open = False
            return
        if key == pygame.K_j:
            session.log_open = not session.log_open
            session.log_scroll = 0
            session.map_open = False
            session.phone_open = False
            return
        if key == pygame.K_q:
            self._throw_bottle()
            return
        if key == pygame.K_e:
            self._try_interact()

    def _handle_play_click(self, mouse_pos: tuple[int, int]) -> None:
        session = self.session
        if session is None or not session.paused:
            return
        for index, (rect, action) in enumerate(self.pause_buttons):
            if rect.collidepoint(mouse_pos):
                session.pause_selection = index
                self._activate_pause_action(index)
                return

    def _activate_pause_action(self, selection: int) -> None:
        if self.session is None:
            return
        if selection == 0:
            self.session.paused = False
            return
        if selection == 1:
            self.view = "menu"
            self.session.paused = False
            return
        if selection == 2:
            self.running = False

    def _toggle_fullscreen(self) -> None:
        if not self.fullscreen:
            self.windowed_resolution = self.screen.get_size()
        self.fullscreen = not self.fullscreen
        self.screen = self._apply_display_mode()
        self._refresh_theme()

    def _toggle_language(self) -> None:
        self.selected_language = "en-US" if self.selected_language == "zh-CN" else "zh-CN"
        self.save_state.language = self.selected_language
        self.localizer.set_language(self.selected_language)
        self.save_manager.save(self.save_state)

    def _toggle_accessibility(self, key: str) -> None:
        current = bool(self.save_state.accessibility_settings.get(key, False))
        self.save_state.accessibility_settings[key] = not current
        self.save_manager.save(self.save_state)
        if key == "high_contrast":
            self._refresh_theme()

    def _close_overlay_panels(self) -> None:
        session = self.session
        if session is None:
            return
        session.phone_open = False
        session.map_open = False
        session.log_open = False

    def _subtitles_enabled(self) -> bool:
        return bool(self.save_state.accessibility_settings.get("subtitles", True))

    def _high_contrast_enabled(self) -> bool:
        return bool(self.save_state.accessibility_settings.get("high_contrast", False))

    def _current_scene(self) -> SceneData:
        session = self.session
        assert session is not None
        scene = self.content.scene_by_id(session.scene_id)
        if scene is None:
            raise ValueError(f"Unknown scene id: {session.scene_id}")
        return scene

    def _camera_offset(self) -> tuple[int, int]:
        scene = self._current_scene()
        session = self.session
        assert session is not None
        width, height = self.screen.get_size()
        max_x = max(0, scene.width - width)
        max_y = max(0, scene.height - height)
        offset_x = max(0, min(int(session.player_x - width / 2), max_x))
        offset_y = max(0, min(int(session.player_y - height / 2), max_y))
        return offset_x, offset_y

    def _update_play(self, dt: float) -> None:
        session = self.session
        if session is None or session.paused or session.outcome:
            return
        if session.opening_active:
            self._update_opening(dt)
            return
        session.elapsed += dt
        self._advance_alerts()
        if session.current_wave_index >= 0:
            first_at = self.content.scenario.alert_waves[0].at
            session.alert_elapsed = max(0.0, session.elapsed - float(first_at))
        self._move_player(dt)
        self._update_room_tracking()
        self._update_actor_ai(dt)
        self._update_noise(dt)
        self._process_proximity_interactions()
        self._evaluate_areas(dt)
        self._check_survive_ending()

    def _process_proximity_interactions(self) -> None:
        session = self.session
        assert session is not None
        for interaction in self.content.interactions:
            if (
                interaction.scene_id != session.scene_id
                or interaction.trigger_mode != "proximity"
                or not phase_allows(session.phase, interaction.state_rules)
                or interaction.id in session.interactions_used
            ):
                continue
            if self._distance((session.player_x, session.player_y), interaction.center()) <= interaction.trigger_radius:
                self._handle_interaction(interaction)

    def _update_opening(self, dt: float) -> None:
        session = self.session
        assert session is not None
        beats = self.content.scenario.opening_sequence
        if not beats:
            session.opening_active = False
            return
        session.opening_timer -= dt
        if session.opening_timer <= 0:
            self._next_opening_beat()

    def _next_opening_beat(self) -> None:
        session = self.session
        assert session is not None
        beats = self.content.scenario.opening_sequence
        session.opening_index += 1
        if session.opening_index >= len(beats):
            session.opening_active = False
            self._post_message("system", "system.opening_done", "objective.explore")
            return
        session.opening_timer = beats[session.opening_index].duration

    def _skip_opening(self) -> None:
        session = self.session
        assert session is not None
        session.opening_active = False
        self._post_message("system", "system.opening_skipped", "objective.explore")

    def _advance_alerts(self) -> None:
        session = self.session
        assert session is not None
        waves = self.content.scenario.alert_waves
        next_index = session.current_wave_index + 1
        while next_index < len(waves) and session.elapsed >= waves[next_index].at:
            if session.current_wave_index >= 0 and session.unread_alert:
                session.ignored_alerts += 1
            wave = waves[next_index]
            session.current_wave_index = next_index
            session.phase = wave.phase
            session.blocked_links = set(wave.blocked_link_ids)
            session.unread_alert = True
            self._post_message("alert", wave.title_key, wave.body_key, record_alert=True)
            if session.ignored_alerts >= 2:
                self._finish_session("fail", "failure.ignored_updates", "failed")
                return
            next_index += 1

    def _acknowledge_alert(self) -> None:
        session = self.session
        assert session is not None
        if session.current_wave_index >= 0 and session.unread_alert:
            session.unread_alert = False
            session.score.add("official_info", 5)

    def _move_player(self, dt: float) -> None:
        session = self.session
        assert session is not None
        if session.phone_open or session.map_open or session.log_open:
            return
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
            float(keys[pygame.K_s]) - float(keys[pygame.K_w]),
        )
        if direction.length_squared() == 0:
            return
        direction = direction.normalize()
        session.last_dir_x = float(direction.x)
        session.last_dir_y = float(direction.y)
        speed = 240
        scene = self._current_scene()
        trial_x = session.player_x + direction.x * speed * dt
        trial_y = session.player_y
        if not self._collides(scene, trial_x, trial_y):
            session.player_x = trial_x
        trial_y = session.player_y + direction.y * speed * dt
        if not self._collides(scene, session.player_x, trial_y):
            session.player_y = trial_y

    def _collides(self, scene: SceneData, px: float, py: float, size: int = 28) -> bool:
        rect = pygame.Rect(int(px - size / 2), int(py - size / 2), size, size)
        if rect.left < 0 or rect.top < 0 or rect.right > scene.width or rect.bottom > scene.height:
            return True
        for collision in scene.blockers():
            if rect.colliderect(pygame.Rect(collision.x, collision.y, collision.width, collision.height)):
                return True
        return False

    def _distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    def _has_clear_line(self, scene: SceneData, start: tuple[float, float], end: tuple[float, float]) -> bool:
        steps = 12
        for idx in range(1, steps):
            t = idx / steps
            px = start[0] + (end[0] - start[0]) * t
            py = start[1] + (end[1] - start[1]) * t
            probe = pygame.Rect(int(px - 4), int(py - 4), 8, 8)
            for blocker in scene.blockers():
                blocker_rect = pygame.Rect(blocker.x, blocker.y, blocker.width, blocker.height)
                if probe.colliderect(blocker_rect):
                    return False
        return True

    def _next_scene_step(self, current_scene_id: str, target_scene_id: str) -> str | None:
        path = self._scene_path(current_scene_id, target_scene_id, allow_blocked=False)
        if len(path) <= 1:
            return current_scene_id if current_scene_id == target_scene_id else None
        return path[1]

    def _link_is_blocked(self, scene: SceneData, link: SceneLink) -> bool:
        session = self.session
        if session is None:
            return False
        return session.phase in {"Alert", "Shelter"} and (link.id in session.blocked_links or link.locked_on_alert)

    def _scene_path(self, start_scene_id: str, target_scene_id: str, *, allow_blocked: bool) -> list[str]:
        if start_scene_id == target_scene_id:
            return [start_scene_id]
        queue: deque[str] = deque([start_scene_id])
        visited = {start_scene_id}
        parent: dict[str, str] = {}
        found = False
        while queue:
            node = queue.popleft()
            scene = self.content.scene_by_id(node)
            if scene is None:
                continue
            for link in scene.links:
                if not allow_blocked and self._link_is_blocked(scene, link):
                    continue
                neighbor = link.target_scene_id
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor] = node
                if neighbor == target_scene_id:
                    found = True
                    queue.clear()
                    break
                queue.append(neighbor)
        if not found:
            return []
        path = [target_scene_id]
        while path[-1] != start_scene_id:
            path.append(parent[path[-1]])
        path.reverse()
        return path

    def _dispatch_raider_to_scene(
        self,
        definition: ActorDefinition,
        runtime: ActorRuntime,
        target_scene_id: str,
        dt: float,
        *,
        force_transfer: bool = False,
    ) -> None:
        if runtime.scene_id == target_scene_id:
            return
        next_scene = self._next_scene_step(runtime.scene_id, target_scene_id)
        if not next_scene or next_scene == runtime.scene_id:
            return
        scene = self.content.scene_by_id(runtime.scene_id)
        if scene is None:
            return
        links = [link for link in scene.links if link.target_scene_id == next_scene]
        if not links:
            return
        link = min(links, key=lambda item: self._distance(runtime.position(), item.center()))
        reached = force_transfer or self._actor_seek(runtime, link.center(), dt, definition.speed + 24)
        if not reached:
            return
        target_scene = self.content.scene_by_id(link.target_scene_id)
        if target_scene is None:
            return
        spawn = target_scene.spawn_by_id(link.target_spawn_id)
        if spawn is None:
            return
        runtime.scene_id = target_scene.id
        runtime.x = spawn.x + spawn.width / 2
        runtime.y = spawn.y + spawn.height / 2
        runtime.state = "Search"
        runtime.search_timer = 2.8

    def _update_room_tracking(self) -> None:
        session = self.session
        assert session is not None
        scene = self._current_scene()
        room = scene.room_at(session.player_x, session.player_y)
        session.current_room_id = room.id if room else ""

    def _update_noise(self, dt: float) -> None:
        active: list[NoiseEvent] = []
        for noise in self.noises:
            noise.timer -= dt
            if noise.timer > 0:
                active.append(noise)
        self.noises = active

    def _nearest_noise(self, scene_id: str, x: float, y: float, radius: float) -> NoiseEvent | None:
        candidates = [
            noise
            for noise in self.noises
            if noise.scene_id == scene_id and self._distance((x, y), (noise.x, noise.y)) <= radius
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda noise: self._distance((x, y), (noise.x, noise.y)))

    def _scene_nav_path(
        self,
        scene_id: str,
        start: tuple[float, float],
        target: tuple[float, float],
    ) -> list[tuple[float, float]]:
        scene = self.content.scene_by_id(scene_id)
        if scene is None:
            return []
        if self._has_clear_line(scene, start, target):
            return [target]
        graph = self.scene_nav_graphs.get(scene_id, {})
        points: list[tuple[float, float]] = list(graph.get("points", []))
        adjacency: dict[int, list[tuple[int, float]]] = dict(graph.get("adjacency", {}))
        if not points:
            return []

        start_candidates = [
            (index, self._distance(start, point))
            for index, point in enumerate(points)
            if self._has_clear_line(scene, start, point)
        ]
        end_candidates = [
            (index, self._distance(target, point))
            for index, point in enumerate(points)
            if self._has_clear_line(scene, point, target)
        ]
        if not start_candidates or not end_candidates:
            return []

        end_lookup = {index: distance for index, distance in end_candidates}
        frontier: list[tuple[float, float, int]] = []
        cost_so_far: dict[int, float] = {}
        parent: dict[int, int | None] = {}
        for index, entry_cost in start_candidates:
            heuristic = min(self._distance(points[index], points[end_index]) for end_index, _ in end_candidates)
            heappush(frontier, (entry_cost + heuristic, entry_cost, index))
            if index not in cost_so_far or entry_cost < cost_so_far[index]:
                cost_so_far[index] = entry_cost
                parent[index] = None

        best_end: int | None = None
        while frontier:
            _, current_cost, node = heappop(frontier)
            if current_cost > cost_so_far.get(node, float("inf")) + 1e-6:
                continue
            if node in end_lookup:
                best_end = node
                break
            for neighbor, edge_cost in adjacency.get(node, []):
                next_cost = current_cost + edge_cost
                if next_cost + 1e-6 < cost_so_far.get(neighbor, float("inf")):
                    cost_so_far[neighbor] = next_cost
                    parent[neighbor] = node
                    heuristic = min(self._distance(points[neighbor], points[end_index]) for end_index, _ in end_candidates)
                    heappush(frontier, (next_cost + heuristic, next_cost, neighbor))

        if best_end is None:
            return []

        route_nodes = [best_end]
        while parent[route_nodes[-1]] is not None:
            route_nodes.append(parent[route_nodes[-1]])
        route_nodes.reverse()
        route = [points[index] for index in route_nodes]
        if not route or self._distance(route[-1], target) > 6:
            route.append(target)
        return route

    def _set_search_origin(self, runtime: ActorRuntime, origin: tuple[float, float]) -> None:
        runtime.search_origin_x = float(origin[0])
        runtime.search_origin_y = float(origin[1])
        runtime.search_step = 0
        runtime.route_points = []
        runtime.route_index = 0

    def _build_search_route(self, runtime: ActorRuntime) -> list[tuple[float, float]]:
        scene = self.content.scene_by_id(runtime.scene_id)
        if scene is None:
            return []
        origin = (runtime.search_origin_x or runtime.x, runtime.search_origin_y or runtime.y)
        offsets = ((0, 0), (120, 0), (0, 120), (-120, 0), (0, -120), (120, 120), (-120, 120))
        points: list[tuple[float, float]] = []
        start = runtime.search_step % len(offsets)
        for index in range(len(offsets)):
            dx, dy = offsets[(start + index) % len(offsets)]
            point = (
                max(48, min(scene.width - 48, origin[0] + dx)),
                max(48, min(scene.height - 48, origin[1] + dy)),
            )
            if self._collides(scene, point[0], point[1], size=26):
                continue
            path = self._scene_nav_path(runtime.scene_id, runtime.position(), point)
            if path:
                points.extend(path)
                runtime.search_step = (start + index + 1) % len(offsets)
                break
        return points

    def _actor_seek(self, runtime: ActorRuntime, target: tuple[float, float], dt: float, speed: float) -> bool:
        scene = self.content.scene_by_id(runtime.scene_id)
        if scene is None:
            return False
        runtime.target_x = float(target[0])
        runtime.target_y = float(target[1])
        if self._has_clear_line(scene, runtime.position(), target):
            runtime.route_points = []
            runtime.route_index = 0
            runtime.route_recalc_timer = 0.0
            return self._actor_move_towards(runtime, target, dt, speed)
        runtime.route_recalc_timer -= dt
        if runtime.route_recalc_timer <= 0 or not runtime.route_points or runtime.route_index >= len(runtime.route_points):
            runtime.route_points = self._scene_nav_path(runtime.scene_id, runtime.position(), target)
            runtime.route_index = 0
            runtime.route_recalc_timer = 0.55
        if runtime.route_points:
            waypoint = runtime.route_points[min(runtime.route_index, len(runtime.route_points) - 1)]
            reached = self._actor_move_towards(runtime, waypoint, dt, speed)
            if reached:
                runtime.route_index += 1
                if runtime.route_index >= len(runtime.route_points):
                    runtime.route_points = []
                    runtime.route_index = 0
                    return self._distance(runtime.position(), target) <= 18
        return self._distance(runtime.position(), target) <= 18

    def _actor_move_towards(self, runtime: ActorRuntime, target: tuple[float, float], dt: float, speed: float) -> bool:
        scene = self.content.scene_by_id(runtime.scene_id)
        if scene is None:
            return False
        vector = pygame.Vector2(target[0] - runtime.x, target[1] - runtime.y)
        distance = vector.length()
        if distance < 1:
            return True
        direction = vector.normalize()
        step = min(distance, speed * dt)
        trial_x = runtime.x + direction.x * step
        trial_y = runtime.y
        if not self._collides(scene, trial_x, trial_y, size=28):
            runtime.x = trial_x
        trial_y = runtime.y + direction.y * step
        if not self._collides(scene, runtime.x, trial_y, size=28):
            runtime.y = trial_y
        runtime.heading_x = float(direction.x)
        runtime.heading_y = float(direction.y)
        return self._distance(runtime.position(), target) <= 8

    def _update_actor_ai(self, dt: float) -> None:
        session = self.session
        assert session is not None
        if session.last_seen_timer > 0:
            session.last_seen_timer -= dt
            if session.last_seen_timer <= 0:
                session.last_seen_scene_id = ""
        seen_any = False
        for actor_id, runtime in self.actor_states.items():
            runtime.hint_cooldown = max(0.0, runtime.hint_cooldown - dt)
            definition = self.actor_defs[actor_id]
            if runtime.kind == "robot":
                self._update_robot(definition, runtime, dt)
            else:
                seen_any = self._update_raider(definition, runtime, dt) or seen_any
        if seen_any:
            was_active = session.global_chase_active
            session.global_chase_active = True
            session.global_chase_timer = 12.0
            if not was_active:
                self._post_message("alert", "ui.chase_broadcast", "ui.chase_broadcast_hint")
        elif session.global_chase_active:
            session.global_chase_timer -= dt
            if session.global_chase_timer <= 0:
                session.global_chase_active = False
        if session.captured:
            self._finish_session("fail", "failure.captured", "failed")

    def _update_robot(self, definition: ActorDefinition, runtime: ActorRuntime, dt: float) -> None:
        session = self.session
        assert session is not None
        patrol = definition.patrol if definition.patrol else ((definition.x, definition.y),)
        target = patrol[runtime.path_index % len(patrol)]
        reached = self._actor_seek(runtime, target, dt, definition.speed)
        if reached:
            runtime.path_index = (runtime.path_index + 1) % len(patrol)
        if definition.noise_interval > 0:
            runtime.noise_timer -= dt
            if runtime.noise_timer <= 0:
                self.noises.append(NoiseEvent(runtime.scene_id, runtime.x, runtime.y, 2.4))
                runtime.noise_timer = definition.noise_interval
                if session.scene_id == runtime.scene_id and self._distance((session.player_x, session.player_y), runtime.position()) < 260:
                    self._post_message("system", "robot.service.notice", definition.hint_key or "robot.service.hint")
        if definition.role == "security" and session.scene_id == runtime.scene_id and runtime.hint_cooldown <= 0:
            nearby_raider = next(
                (
                    actor
                    for actor in self.actor_states.values()
                    if actor.kind == "raider"
                    and actor.scene_id == runtime.scene_id
                    and self._distance(actor.position(), runtime.position()) < 320
                ),
                None,
            )
            if nearby_raider is not None:
                self._post_message("system", "robot.security.notice", definition.hint_key or "robot.security.hint")
                runtime.hint_cooldown = 7.0
        elif definition.role == "guide" and session.scene_id == runtime.scene_id and session.phase == "Explore" and runtime.hint_cooldown <= 0:
            if self._distance((session.player_x, session.player_y), runtime.position()) < 220:
                self._post_message("system", "robot.guide.notice", definition.hint_key or "robot.guide.hint")
                runtime.hint_cooldown = 9.0

    def _raider_sees_player(self, definition: ActorDefinition, runtime: ActorRuntime) -> bool:
        session = self.session
        assert session is not None
        if runtime.scene_id != session.scene_id:
            return False
        scene = self.content.scene_by_id(runtime.scene_id)
        if scene is None:
            return False
        vector = pygame.Vector2(session.player_x - runtime.x, session.player_y - runtime.y)
        distance = vector.length()
        if distance > definition.vision_distance:
            return False
        if distance < 1:
            return True
        direction = vector.normalize()
        heading = pygame.Vector2(runtime.heading_x, runtime.heading_y)
        if heading.length_squared() == 0:
            heading = pygame.Vector2(1, 0)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, heading.dot(direction)))))
        if angle > definition.vision_deg / 2:
            return False
        return self._has_clear_line(scene, runtime.position(), (session.player_x, session.player_y))

    def _update_raider(self, definition: ActorDefinition, runtime: ActorRuntime, dt: float) -> bool:
        session = self.session
        assert session is not None
        if (
            session.global_chase_active
            and definition.can_cross_scene
            and runtime.scene_id != session.scene_id
        ):
            if runtime.state != "Dispatch":
                runtime.search_timer = 2.4
            runtime.state = "Dispatch"
            runtime.search_timer -= dt
            force_transfer = runtime.search_timer <= 0
            self._dispatch_raider_to_scene(
                definition,
                runtime,
                session.scene_id,
                dt,
                force_transfer=force_transfer,
            )
            if force_transfer:
                runtime.search_timer = 2.4
            return False

        patrol = definition.patrol if definition.patrol else ((definition.x, definition.y),)
        seen = self._raider_sees_player(definition, runtime)
        heard = self._nearest_noise(runtime.scene_id, runtime.x, runtime.y, definition.hearing_radius)

        if seen:
            runtime.alert_meter = min(2.0, runtime.alert_meter + dt * 2.8)
        else:
            runtime.alert_meter = max(0.0, runtime.alert_meter - dt * 1.2)

        if runtime.alert_meter >= 0.85:
            runtime.state = "Chase"
            runtime.target_x = session.player_x
            runtime.target_y = session.player_y
            runtime.lost_timer = 0.0
            runtime.guard_leave_timer = 0.0
            session.last_seen_scene_id = session.scene_id
            session.last_seen_x = session.player_x
            session.last_seen_y = session.player_y
            session.last_seen_timer = 8.0
        elif runtime.state != "Chase" and heard is not None:
            runtime.state = "InvestigateNoise"
            runtime.target_x = heard.x
            runtime.target_y = heard.y
            self._set_search_origin(runtime, (heard.x, heard.y))
        elif (
            session.global_chase_active
            and session.last_seen_scene_id == runtime.scene_id
            and session.last_seen_timer > 0
            and runtime.state in {"Patrol", "Return", "Search"}
        ):
            runtime.state = "InvestigateNoise"
            runtime.target_x = session.last_seen_x
            runtime.target_y = session.last_seen_y
            self._set_search_origin(runtime, (session.last_seen_x, session.last_seen_y))

        if runtime.state == "Patrol":
            target = patrol[runtime.path_index % len(patrol)]
            reached = self._actor_seek(runtime, target, dt, definition.speed)
            if reached:
                runtime.path_index = (runtime.path_index + 1) % len(patrol)
        elif runtime.state == "InvestigateNoise":
            reached = self._actor_seek(runtime, (runtime.target_x, runtime.target_y), dt, definition.speed + 12)
            if reached:
                runtime.state = "Search"
                runtime.search_timer = 4.0
                self._set_search_origin(runtime, (runtime.target_x, runtime.target_y))
        elif runtime.state == "Chase":
            if runtime.scene_id == session.scene_id:
                self._actor_seek(runtime, (session.player_x, session.player_y), dt, definition.speed + 34)
                if self._distance(runtime.position(), (session.player_x, session.player_y)) < 28:
                    session.captured = True
                    return
            if seen:
                runtime.lost_timer = 0
            else:
                runtime.lost_timer += dt
                if runtime.lost_timer > 2.0:
                    runtime.state = "Search"
                    runtime.search_timer = 8.0
                    self._set_search_origin(runtime, (session.last_seen_x or runtime.x, session.last_seen_y or runtime.y))
        elif runtime.state == "Search":
            runtime.search_timer -= dt
            if heard is not None:
                runtime.target_x = heard.x
                runtime.target_y = heard.y
                self._set_search_origin(runtime, (heard.x, heard.y))
            if not runtime.route_points:
                runtime.route_points = self._build_search_route(runtime)
                runtime.route_index = 0
            if runtime.route_points:
                waypoint = runtime.route_points[min(runtime.route_index, len(runtime.route_points) - 1)]
                reached = self._actor_seek(runtime, waypoint, dt, definition.speed + 6)
                if reached:
                    runtime.route_index += 1
                    if runtime.route_index >= len(runtime.route_points):
                        runtime.route_points = []
                        runtime.route_index = 0
            if runtime.search_timer <= 0:
                runtime.state = "Return"
                runtime.route_points = []
                runtime.route_index = 0
        elif runtime.state == "Return":
            nearest_index = min(
                range(len(patrol)),
                key=lambda idx: self._distance(runtime.position(), (float(patrol[idx][0]), float(patrol[idx][1]))),
            )
            runtime.path_index = nearest_index
            target = patrol[nearest_index]
            reached = self._actor_seek(runtime, target, dt, definition.speed + 6)
            if reached:
                runtime.state = "Patrol"

        if definition.dispatch_role == "guard":
            anchor = definition.fallback_anchor if definition.fallback_anchor != (0, 0) else patrol[0]
            anchor_distance = self._distance(runtime.position(), (float(anchor[0]), float(anchor[1])))
            if session.global_chase_active and anchor_distance > 140 and not seen:
                runtime.guard_leave_timer += dt
            else:
                runtime.guard_leave_timer = max(0.0, runtime.guard_leave_timer - dt * 1.5)
            if runtime.guard_leave_timer > 14.0 and runtime.scene_id == definition.scene_id:
                runtime.state = "Return"
                runtime.path_index = min(
                    range(len(patrol)),
                    key=lambda idx: self._distance(
                        runtime.position(), (float(patrol[idx][0]), float(patrol[idx][1]))
                    ),
                )
        return seen

    def _evaluate_areas(self, dt: float) -> None:
        session = self.session
        assert session is not None
        if session.phase not in {"Alert", "Shelter"}:
            session.exposure_seconds = max(0.0, session.exposure_seconds - dt)
            session.reverse_risk_seconds = 0.0
            return
        scene = self._current_scene()
        safe = scene.safe_area_at(session.player_x, session.player_y)
        risk = scene.risk_area_at(session.player_x, session.player_y)
        safe_qualified = safe is not None and qualifies_safe_area(safe, self.content.scenario.safe_room_tags)
        if safe_qualified:
            session.safe_seconds += dt
            session.exposure_seconds = max(0.0, session.exposure_seconds - dt * 2)
            session.reverse_risk_seconds = 0.0
        else:
            if session.phase == "Shelter" and session.safe_seconds >= 10:
                session.reverse_risk_seconds += dt
                if session.reverse_risk_seconds > 6:
                    self._finish_session("fail", "failure.reverse_risk", "failed")
                    return
        if risk is not None and not safe_qualified:
            session.exposure_seconds += dt
        else:
            session.exposure_seconds = max(0.0, session.exposure_seconds - dt)
        if session.exposure_seconds > 14:
            self._finish_session("fail", "failure.high_risk_area", "failed")

    def _check_survive_ending(self) -> None:
        session = self.session
        assert session is not None
        if session.outcome:
            return
        survive_seconds = int(self.content.scenario.ending_conditions.get("survive_seconds", 420))
        if session.current_wave_index >= 0 and session.alert_elapsed >= survive_seconds and session.safe_seconds >= 20:
            self._finish_session("success", "success.police_arrival", "police_arrival")

    def _score_action(self, action: str) -> None:
        session = self.session
        assert session is not None
        category, amount = ACTION_SCORE_MAP.get(action, ("knowledge_collection", 1))
        session.score.add(category, amount)

    def _nearest_interaction(self) -> Interaction | None:
        session = self.session
        assert session is not None
        candidates = [
            item
            for item in self.content.interactions
            if item.scene_id == session.scene_id
            and phase_allows(session.phase, item.state_rules)
            and item.trigger_mode == "press"
        ]
        if not candidates:
            return None
        nearest = min(
            candidates,
            key=lambda interaction: self._distance((session.player_x, session.player_y), interaction.center()),
        )
        if self._distance((session.player_x, session.player_y), nearest.center()) <= nearest.trigger_radius:
            return nearest
        return None

    def _current_exit_zone(self) -> ExitZone | None:
        session = self.session
        assert session is not None
        scene = self._current_scene()
        zone = scene.exit_zone_at(session.player_x, session.player_y)
        if zone and phase_allows(session.phase, zone.state_rules):
            return zone
        return None

    def _nearest_link(self) -> SceneLink | None:
        session = self.session
        assert session is not None
        scene = self._current_scene()
        direct = scene.link_at(session.player_x, session.player_y)
        if direct is not None:
            return direct
        nearest = min(
            scene.links,
            key=lambda link: self._distance((session.player_x, session.player_y), link.center()),
            default=None,
        )
        if nearest and self._distance((session.player_x, session.player_y), nearest.center()) <= 85:
            return nearest
        return None

    def _nearest_robot(self) -> ActorRuntime | None:
        session = self.session
        assert session is not None
        robots = [runtime for runtime in self.actor_states.values() if runtime.kind == "robot" and runtime.scene_id == session.scene_id]
        if not robots:
            return None
        nearest = min(robots, key=lambda runtime: self._distance((session.player_x, session.player_y), runtime.position()))
        if self._distance((session.player_x, session.player_y), nearest.position()) <= 95:
            return nearest
        return None

    def _can_open_map(self) -> bool:
        session = self.session
        assert session is not None
        scene = self._current_scene()
        return scene.nearest_board(session.player_x, session.player_y, max_distance=95) is not None

    def _throw_bottle(self) -> None:
        session = self.session
        assert session is not None
        if session.bottles <= 0:
            self._post_message("system", "ui.bottle_empty", "ui.bottle_hint")
            return
        direction = pygame.Vector2(session.last_dir_x, session.last_dir_y)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(0, -1)
        direction = direction.normalize()
        scene = self._current_scene()
        target_x = session.player_x + direction.x * 240
        target_y = session.player_y + direction.y * 240
        target_x = max(60, min(scene.width - 60, target_x))
        target_y = max(60, min(scene.height - 60, target_y))
        self.noises.append(NoiseEvent(session.scene_id, target_x, target_y, 3.5))
        session.bottles -= 1
        session.bottle_throws += 1
        session.unlocked_terms.add("decoy_noise")
        self._score_action("bottle_pickup")
        self._post_message("system", "ui.throw_bottle", "ui.throw_bottle_result")

    def _try_interact(self) -> None:
        exit_zone = self._current_exit_zone()
        if exit_zone:
            self._handle_exit_zone(exit_zone)
            return
        interaction = self._nearest_interaction()
        if interaction:
            self._handle_interaction(interaction)
            return
        link = self._nearest_link()
        if link:
            self._handle_link(link)
            return
        robot = self._nearest_robot()
        if robot:
            self._handle_robot(robot)
            return
        self._post_message("system", "ui.current_prompt", "status.controls")

    def _handle_exit_zone(self, zone: ExitZone) -> None:
        session = self.session
        assert session is not None
        session.exit_attempts += 1
        if zone.action == "north_exit":
            self._score_action("north_exit")
            self._attempt_gate_exit()
            return
        if zone.action == "secret_tunnel":
            self._score_action("secret_tunnel")
            self._attempt_secret_exit()
            return
        self._post_message("system", zone.label_key, "ui.read_alert_hint")

    def _handle_link(self, link: SceneLink) -> None:
        session = self.session
        assert session is not None
        if session.phase in {"Alert", "Shelter"} and (link.id in session.blocked_links or link.locked_on_alert):
            self._post_message("system", "ui.link_blocked", "ui.link_blocked_hint")
            return
        target_scene = self.content.scene_by_id(link.target_scene_id)
        if target_scene is None:
            return
        spawn = target_scene.spawn_by_id(link.target_spawn_id)
        if spawn is None:
            return
        session.scene_id = target_scene.id
        session.player_x = spawn.x + spawn.width / 2
        session.player_y = spawn.y + spawn.height / 2
        session.floor_changes += 1
        self._close_overlay_panels()
        self._update_room_tracking()
        self._post_message("system", "ui.transfer_done", link.label_key)

    def _handle_interaction(self, interaction: Interaction) -> None:
        session = self.session
        assert session is not None
        if not phase_allows(session.phase, interaction.state_rules):
            return
        if interaction.requires_item and interaction.requires_item not in session.inventory:
            feedback = interaction.fail_feedback_key or "ui.requires_item"
            self._post_message("system", feedback, "ui.requires_item")
            return
        if interaction.unlock_flag and interaction.unlock_flag not in session.clues_found:
            feedback = interaction.fail_feedback_key or "ui.secret_locked"
            self._post_message("system", feedback, "ui.secret_locked_hint")
            return
        if interaction.id not in session.interactions_used:
            session.interactions_used.add(interaction.id)
            if interaction.education_key:
                session.unlocked_terms.add(interaction.education_key)
            self._score_action(interaction.action)
        action_key = f"action_result.{interaction.action}"
        if interaction.action == "map_board":
            session.map_open = True
            session.map_reads += 1
            self._post_message("learning", interaction.label_key, "ui.map_opened")
            return
        if interaction.action in {"broadcast", "phone_sync"}:
            self._acknowledge_alert()
            self._post_message("learning", interaction.label_key, action_key)
            return
        if interaction.action == "safe_room_check":
            scene = self._current_scene()
            safe = scene.safe_area_at(session.player_x, session.player_y)
            if safe and qualifies_safe_area(safe, self.content.scenario.safe_room_tags):
                self._post_message("learning", "ui.safe_room_yes", safe.label_key)
            else:
                self._post_message("learning", "ui.safe_room_no", "ui.read_alert_hint")
            return
        if interaction.action == "bottle_pickup":
            session.bottles = min(6, session.bottles + 1)
            session.inventory.add("bottle")
            self._post_message("learning", "ui.bottle_pickup", action_key)
            return
        if interaction.action == "clue_collect":
            if interaction.id not in session.clues_found:
                session.clues_found.add(interaction.id)
            self._post_message("learning", interaction.label_key, "ui.clue_progress")
            return
        if interaction.action == "north_exit":
            self._attempt_gate_exit()
            return
        if interaction.action == "secret_tunnel":
            self._attempt_secret_exit()
            return
        self._post_message("learning", interaction.label_key, action_key)

    def _attempt_gate_exit(self) -> None:
        session = self.session
        assert session is not None
        block_reason = self._gate_exit_block_reason()
        if block_reason:
            self._post_message("system", block_reason, "ui.exit_blocked_hint")
            return
        self._finish_session("success", "success.exit_gate", "exit_gate")

    def _attempt_secret_exit(self) -> None:
        session = self.session
        assert session is not None
        required = int(self.content.scenario.ending_conditions.get("required_clues", 3))
        if len(session.clues_found) < required:
            self._post_message("system", "ui.secret_locked", "ui.secret_need_clues")
            return
        self._finish_session("success", "success.secret_tunnel", "secret_tunnel")

    def _gate_exit_block_reason(self) -> str | None:
        session = self.session
        assert session is not None
        if session.scene_id != "outdoor_main":
            return "ui.exit_not_in_gate_scene"
        guard = self.actor_states.get("raider_gate_guard")
        if not guard or guard.scene_id != session.scene_id:
            return None
        guard_def = self.actor_defs.get("raider_gate_guard")
        distance = self._distance((guard.x, guard.y), (session.player_x, session.player_y))
        near_noise = self._nearest_noise(guard.scene_id, guard.x, guard.y, 180) is not None
        guard_sees = self._raider_sees_player(guard_def, guard) if guard_def else False
        distracted = guard.state in {"InvestigateNoise", "Dispatch", "Search"} or near_noise
        if distance < 260 and guard_sees and not distracted:
            return "ui.exit_blocked_guardline"
        if distance < 180 and not near_noise and guard.state == "Patrol":
            return "ui.exit_blocked_noise"
        return None

    def _route_to_scene_labels(self, target_scene_id: str) -> tuple[list[str], str]:
        session = self.session
        assert session is not None
        route = self._scene_path(session.scene_id, target_scene_id, allow_blocked=False)
        if not route:
            fallback = self._scene_path(session.scene_id, target_scene_id, allow_blocked=True)
            fallback_labels = [self.localizer.text(self.content.scenes[item].floor_label_key) for item in fallback] if fallback else []
            return fallback_labels, "ui.map_route_blocked"
        labels = [self.localizer.text(self.content.scenes[item].floor_label_key) for item in route]
        return labels, "ui.map_route_open"

    def _current_advisory(self) -> AdvisoryDecision:
        session = self.session
        assert session is not None
        scene = self._current_scene()
        room = scene.room_at(session.player_x, session.player_y)
        safe = scene.safe_area_at(session.player_x, session.player_y)
        safe_qualified = safe is not None and qualifies_safe_area(safe, self.content.scenario.safe_room_tags)
        required_clues = int(self.content.scenario.ending_conditions.get("required_clues", 3))
        survive_seconds = int(self.content.scenario.ending_conditions.get("survive_seconds", 420))
        gate_route, _ = self._route_to_scene_labels("outdoor_main")
        secret_route, _ = self._route_to_scene_labels("library_f2")
        gate_reason_key = self._gate_exit_block_reason()
        gate_reason_text = self.localizer.text(gate_reason_key) if gate_reason_key else ""
        route_gate_text = (
            self.localizer.text("ui.map_route_current_scene")
            if session.scene_id == "outdoor_main"
            else (" -> ".join(gate_route) if gate_route else self.localizer.text("ui.map_route_unknown"))
        )
        route_secret_text = (
            self.localizer.text("ui.map_route_current_scene")
            if session.scene_id == "library_f2"
            else (" -> ".join(secret_route) if secret_route else self.localizer.text("ui.map_route_unknown"))
        )
        cache_key = (
            self.selected_language,
            session.scene_id,
            room.id if room else "",
            session.phase,
            len(session.clues_found),
            session.bottles,
            safe_qualified,
            bool(self._can_open_map()),
            gate_reason_key or "",
            session.map_reads,
            int(session.alert_elapsed // 5),
        )
        if cache_key == self._advisory_cache_key and self._advisory_cache is not None:
            return self._advisory_cache
        payload = {
            "scene_id": session.scene_id,
            "phase": session.phase,
            "safe": safe_qualified,
            "near_map_board": self._can_open_map(),
            "clues_found": len(session.clues_found),
            "required_clues": required_clues,
            "bottles": session.bottles,
            "route_gate": route_gate_text,
            "route_secret": route_secret_text,
            "gate_reason": gate_reason_key,
            "gate_reason_text": gate_reason_text,
            "default_gate_reason": self.localizer.text("ui.map_gate_status_move"),
            "default_route_unknown": self.localizer.text("ui.map_route_unknown"),
            "at_gate_scene": session.scene_id == "outdoor_main",
            "alert_elapsed": session.alert_elapsed,
            "survive_seconds": survive_seconds,
            "map_reads": session.map_reads,
            "state_text": (
                f"phase={session.phase}; scene={scene.id}; room={room.id if room else 'unknown'}; "
                f"safe={safe_qualified}; clues={len(session.clues_found)}/{required_clues}; "
                f"bottles={session.bottles}; gate_reason={gate_reason_text or 'open'}; "
                f"route_gate={route_gate_text}; route_secret={route_secret_text}"
            ),
        }
        decision = self.advisor.evaluate(self.selected_language, payload)
        self._advisory_cache_key = cache_key
        self._advisory_cache = decision
        return decision

    def _handle_robot(self, runtime: ActorRuntime) -> None:
        definition = self.actor_defs[runtime.id]
        session = self.session
        assert session is not None
        title_key = definition.label_key or "robot.default.name"
        body_key = definition.hint_key or "robot.default.hint"
        self._post_message("learning", title_key, body_key)
        advisory = self._current_advisory()
        if definition.role in {"guide", "security"}:
            self._post_literal_message("learning", advisory.coach_title, advisory.coach_body)
        if not runtime.hint_used:
            runtime.hint_used = True
            session.unlocked_terms.add("robot_guidance")
            session.score.add("low_risk_assist", 4)

    def _finish_session(self, outcome: str, key: str, ending_type: str) -> None:
        session = self.session
        assert session is not None
        if session.outcome:
            return
        session.phase = "Debrief"
        session.outcome = outcome
        session.outcome_key = key
        session.ending_type = ending_type
        self._persist_session_result()

    def _persist_session_result(self) -> None:
        session = self.session
        assert session is not None
        if session.completion_saved:
            return
        self.save_state.language = self.selected_language
        self.save_state.completed_runs += 1
        self.save_state.best_score = max(self.save_state.best_score, session.score.total())
        self.save_state.unlocked_terms = sorted(set(self.save_state.unlocked_terms) | session.unlocked_terms)
        self.save_state.current_scene = session.scene_id
        scene = self._current_scene()
        self.save_state.current_floor = scene.floor_label_key
        self.save_state.inventory = sorted(session.inventory)
        self.save_state.clues_found = sorted(session.clues_found)
        if session.ending_type != "failed":
            self.save_state.ending_history = (self.save_state.ending_history + [session.ending_type])[-12:]
        self.save_manager.save(self.save_state)
        session.completion_saved = True

    def _post_message(self, kind: str, title_key: str, body_key: str, record_alert: bool = False) -> None:
        session = self.session
        if session is None:
            return
        title = self.localizer.text(title_key)
        body = self.localizer.text(body_key)
        self._post_literal_message(kind, title, body, record_alert=record_alert)

    def _post_literal_message(self, kind: str, title: str, body: str, record_alert: bool = False) -> None:
        session = self.session
        if session is None:
            return
        session.push_subtitle(title, body)
        if not session.message_history or session.message_history[-1] != (kind, title, body):
            session.message_history.append((kind, title, body))
        del session.message_history[:-36]
        if record_alert:
            session.alert_history.append((title, body))
            del session.alert_history[:-10]

    def _render(self) -> None:
        self._draw_backdrop()
        if self.view == "menu":
            self._render_menu()
        elif self.view == "play" and self.session:
            self._render_world()
            self._render_hud()
            self._render_overlays()
        pygame.display.flip()

    def _screen_layout(self):
        return build_screen_layout(self.screen.get_size())

    def _tone(self, name: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        theme = self.ui_theme
        if name == "primary":
            return theme.dark_surface, theme.dark_border, theme.light_ink
        if name == "accent":
            return theme.surface, theme.accent, theme.ink
        if name == "info":
            return theme.surface_alt, theme.info, theme.ink
        if name == "success":
            return theme.surface_alt, theme.success, theme.ink
        if name == "danger":
            return theme.surface_alt, theme.danger, theme.ink
        if name == "warning":
            return theme.surface_alt, theme.warning, theme.ink
        if name == "muted":
            return theme.surface_soft, theme.border, theme.ink
        return theme.surface, theme.border, theme.ink

    def _draw_chip(
        self,
        rect: pygame.Rect,
        title: str,
        value: str,
        *,
        tone: str = "default",
        icon: str | None = None,
        compact: bool = False,
    ) -> None:
        fill, border, text = self._tone(tone)
        glass_fill = (fill[0], fill[1], fill[2], 232)
        self._draw_card(rect, fill=glass_fill, border=border, radius=self.ui_theme.radius_medium, shadow=2)
        band = pygame.Rect(rect.x + 12, rect.y + 12, max(72, int(rect.width * 0.34)), 5)
        pygame.draw.rect(self.screen, border, band, border_radius=3)
        title_rect = pygame.Rect(rect.x + 16, rect.y + 18, rect.width - 28, 16)
        value_rect = pygame.Rect(rect.x + 16, rect.y + 34, rect.width - 28, rect.height - 42)
        title_surface = self.fonts["tiny"].render(title, True, self.ui_theme.muted)
        self.screen.blit(title_surface, title_rect.topleft)
        font_key = "tiny" if compact else "body"
        body_prefix = f"{icon} " if icon else ""
        self._draw_wrapped(
            self.screen,
            self.fonts[font_key],
            f"{body_prefix}{value}",
            text,
            value_rect,
            self.fonts[font_key].get_linesize(),
        )

    def _draw_stat_pill(
        self,
        rect: pygame.Rect,
        label: str,
        value: str,
        *,
        tone: str = "info",
    ) -> None:
        fill, border, _ = self._tone(tone)
        self._draw_card(rect, fill=(fill[0], fill[1], fill[2], 228), border=border, radius=self.ui_theme.radius_small, shadow=1)
        label_surface = self.fonts["tiny"].render(label, True, self.ui_theme.muted)
        value_surface = self.fonts["small"].render(value, True, self.ui_theme.ink)
        self.screen.blit(label_surface, (rect.x + 10, rect.y + 6))
        self.screen.blit(value_surface, value_surface.get_rect(bottomleft=(rect.x + 10, rect.bottom - 8)))

    def _draw_progress_bar(
        self,
        rect: pygame.Rect,
        ratio: float,
        *,
        tone: str = "accent",
    ) -> None:
        _, border, _ = self._tone(tone)
        pygame.draw.rect(self.screen, self.ui_theme.surface_soft, rect, border_radius=rect.height // 2)
        fill_w = max(8, int(rect.width * max(0.0, min(1.0, ratio))))
        pygame.draw.rect(
            self.screen,
            border,
            pygame.Rect(rect.x, rect.y, fill_w, rect.height),
            border_radius=rect.height // 2,
        )

    def _draw_marker_icon(self, center: tuple[int, int], tone: str) -> None:
        _, border, _ = self._tone(tone)
        pygame.draw.circle(self.screen, border, center, 7)
        pygame.draw.circle(self.screen, self.ui_theme.surface, center, 3)

    def _draw_floor_tabs(self, rect: pygame.Rect, current_scene: SceneData) -> None:
        theme = self.ui_theme
        current_building = current_scene.building_key
        floors = [scene for scene in self.content.scenes.values() if scene.building_key == current_building]
        floors.sort(key=lambda item: item.floor_label_key)
        if not floors:
            return
        tab_w = max(92, int((rect.width - theme.gap * (len(floors) - 1)) / max(1, len(floors))))
        x = rect.x
        for scene in floors:
            tab = pygame.Rect(x, rect.y, tab_w, rect.height)
            active = scene.id == current_scene.id
            fill = theme.dark_surface if active else theme.surface_alt
            border = theme.info if active else theme.border
            ink = theme.light_ink if active else theme.ink
            self._draw_card(tab, fill=fill, border=border, radius=theme.radius_small, shadow=2)
            label = self.localizer.text(scene.floor_label_key)
            font = self.fonts["tiny"]
            text = font.render(label, True, ink)
            self.screen.blit(text, text.get_rect(center=tab.center))
            x += tab_w + theme.gap

    def _draw_room_world(self, room: object, rect: pygame.Rect) -> None:
        theme = self.ui_theme
        pygame.draw.rect(self.screen, (230, 234, 235), rect, border_radius=12)
        pygame.draw.rect(self.screen, theme.border, rect, 2, border_radius=12)
        room_id = getattr(room, "id", "")
        if "lobby" in room_id or "atrium" in room_id:
            for x in range(rect.x + 18, rect.right - 18, 44):
                pygame.draw.line(self.screen, (214, 220, 223), (x, rect.y + 10), (x, rect.bottom - 10), 1)
            for y in range(rect.y + 18, rect.bottom - 18, 44):
                pygame.draw.line(self.screen, (214, 220, 223), (rect.x + 10, y), (rect.right - 10, y), 1)
        elif "reading" in room_id or "study" in room_id or "archive" in room_id or "stacks" in room_id:
            for y in range(rect.y + 20, rect.bottom - 12, 36):
                pygame.draw.line(self.screen, (219, 225, 228), (rect.x + 12, y), (rect.right - 12, y), 1)
        elif "classroom" in room_id or "meeting" in room_id or "media" in room_id:
            board = pygame.Rect(rect.x + 16, rect.y + 14, rect.width - 32, 12)
            pygame.draw.rect(self.screen, (72, 100, 81), board, border_radius=4)
            for row_y in range(rect.y + 52, rect.bottom - 24, 58):
                for col_x in range(rect.x + 26, rect.right - 40, 72):
                    pygame.draw.rect(self.screen, (203, 210, 214), pygame.Rect(col_x, row_y, 34, 18), border_radius=4)

    def _draw_prop_world(self, prop: object, rect: pygame.Rect) -> None:
        theme = self.ui_theme
        prop_type = getattr(prop, "type", "prop")
        if prop_type == "bookshelf":
            pygame.draw.rect(self.screen, (108, 72, 42), rect, border_radius=6)
            for x in range(rect.x + 8, rect.right - 6, 14):
                pygame.draw.line(self.screen, (220, 198, 168), (x, rect.y + 6), (x, rect.bottom - 6), 2)
            pygame.draw.rect(self.screen, (70, 44, 26), rect, 2, border_radius=6)
            return
        if prop_type == "desk_cluster":
            pygame.draw.rect(self.screen, (144, 118, 84), rect, border_radius=8)
            center_y = rect.centery
            chair_w = max(10, rect.width // 8)
            pygame.draw.rect(self.screen, (99, 81, 62), pygame.Rect(rect.x + 10, rect.y - 10, chair_w, 10), border_radius=3)
            pygame.draw.rect(self.screen, (99, 81, 62), pygame.Rect(rect.right - chair_w - 10, rect.bottom, chair_w, 10), border_radius=3)
            pygame.draw.line(self.screen, (90, 72, 54), (rect.x + 18, center_y), (rect.right - 18, center_y), 2)
            pygame.draw.rect(self.screen, (96, 77, 55), rect, 2, border_radius=8)
            return
        if prop_type == "service_desk":
            pygame.draw.rect(self.screen, (95, 113, 131), rect, border_radius=8)
            top = pygame.Rect(rect.x, rect.y, rect.width, max(10, rect.height // 3))
            pygame.draw.rect(self.screen, (132, 150, 166), top, border_radius=8)
            pygame.draw.rect(self.screen, theme.border, rect, 2, border_radius=8)
            return
        if prop_type == "divider":
            pygame.draw.rect(self.screen, (122, 132, 140), rect, border_radius=6)
            for y in range(rect.y + 6, rect.bottom - 4, 14):
                pygame.draw.line(self.screen, (196, 204, 210), (rect.x + 4, y), (rect.right - 4, y), 1)
            pygame.draw.rect(self.screen, theme.border, rect, 1, border_radius=6)
            return
        if prop_type == "classroom_block":
            pygame.draw.rect(self.screen, (124, 105, 148), rect, border_radius=8)
            cols = max(2, rect.width // 88)
            rows = max(2, rect.height // 70)
            cell_w = max(26, rect.width // cols - 12)
            cell_h = max(16, rect.height // rows - 10)
            for row in range(rows):
                for col in range(cols):
                    x = rect.x + 12 + col * (cell_w + 10)
                    y = rect.y + 10 + row * (cell_h + 10)
                    cell = pygame.Rect(x, y, cell_w, cell_h)
                    if cell.right < rect.right - 6 and cell.bottom < rect.bottom - 6:
                        pygame.draw.rect(self.screen, (206, 195, 220), cell, border_radius=4)
            pygame.draw.rect(self.screen, (86, 66, 108), rect, 2, border_radius=8)
            return
        pygame.draw.rect(self.screen, (110, 128, 146), rect, border_radius=6)
        pygame.draw.rect(self.screen, theme.border, rect, 1, border_radius=6)

    def _draw_actor_world(self, runtime: ActorRuntime, definition: ActorDefinition, center: tuple[int, int]) -> None:
        theme = self.ui_theme
        if runtime.kind == "robot":
            body = pygame.Rect(center[0] - 13, center[1] - 13, 26, 26)
            pygame.draw.rect(self.screen, theme.info, body, border_radius=7)
            eye = pygame.Rect(body.x + 5, body.y + 8, body.width - 10, 5)
            pygame.draw.rect(self.screen, theme.surface, eye, border_radius=3)
            pygame.draw.rect(self.screen, theme.dark_surface, body, 2, border_radius=7)
            return

        if self.selected_mode == "practice":
            heading = pygame.Vector2(runtime.heading_x, runtime.heading_y)
            if heading.length_squared() == 0:
                heading = pygame.Vector2(1, 0)
            heading = heading.normalize()
            left_vec = heading.rotate(-definition.vision_deg / 2) * min(definition.vision_distance, 180)
            right_vec = heading.rotate(definition.vision_deg / 2) * min(definition.vision_distance, 180)
            cone = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(
                cone,
                (theme.danger[0], theme.danger[1], theme.danger[2], 42),
                [center, (center[0] + left_vec.x, center[1] + left_vec.y), (center[0] + right_vec.x, center[1] + right_vec.y)],
            )
            self.screen.blit(cone, (0, 0))

        pygame.draw.circle(self.screen, theme.danger, center, 13)
        facing = pygame.Vector2(runtime.heading_x, runtime.heading_y)
        if facing.length_squared() == 0:
            facing = pygame.Vector2(1, 0)
        facing = facing.normalize()
        tip = (center[0] + facing.x * 16, center[1] + facing.y * 16)
        left = facing.rotate(135) * 8
        right = facing.rotate(-135) * 8
        pygame.draw.polygon(
            self.screen,
            theme.surface,
            [tip, (center[0] + left.x, center[1] + left.y), (center[0] + right.x, center[1] + right.y)],
        )
        pygame.draw.circle(self.screen, theme.dark_surface, center, 13, 2)

    def _render_menu(self) -> None:
        theme = self.ui_theme
        self.localizer.set_language(self.selected_language)
        layout = self._screen_layout()
        hero = layout.menu_hero
        self._draw_card(hero, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=8)
        accent_panel = pygame.Rect(hero.x, hero.y, 14, hero.height)
        pygame.draw.rect(
            self.screen,
            theme.warning,
            accent_panel,
            border_top_left_radius=theme.radius_large,
            border_bottom_left_radius=theme.radius_large,
        )
        eyebrow = self.fonts["tiny"].render(self.localizer.text("ui.menu_eyebrow"), True, theme.info)
        self.screen.blit(eyebrow, (hero.x + 28, hero.y + 18))
        title = self.fonts["display"].render(self.localizer.text("game.title"), True, theme.ink)
        subtitle = self.fonts["heading"].render(self.localizer.text("menu.subtitle"), True, theme.muted)
        self.screen.blit(title, (hero.x + 24, hero.y + 34))
        self.screen.blit(subtitle, (hero.x + 28, hero.y + 92))
        meta_panel = pygame.Rect(hero.right - 306, hero.y + 18, 278, hero.height - 36)
        badge_rect, meta_rect = stack_rows(meta_panel, [60, meta_panel.height - 60 - theme.small_gap], theme.small_gap)
        self._draw_chip(
            badge_rect,
            self.localizer.text("menu.mode"),
            f"{self.localizer.text(f'mode.{self.selected_mode}')} / {self.localizer.text(f'lang.{self.selected_language}')}",
            tone="info",
            compact=True,
        )
        self._draw_chip(
            meta_rect,
            self.localizer.text("menu.spawn"),
            self.localizer.text(f"spawn.{self.selected_spawn}"),
            tone="accent",
            compact=True,
        )

        visual = layout.menu_visual
        actions = layout.menu_actions
        help_rect = layout.menu_help
        self._draw_card(visual, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=6)
        self._draw_card(actions, fill=theme.paper_alt, border=theme.border, radius=theme.radius_large, shadow=6)
        self._draw_card(help_rect, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=6)

        visual_title = self.fonts["heading"].render(self.localizer.text("ui.menu_route_board"), True, theme.ink)
        self.screen.blit(visual_title, (visual.x + 20, visual.y + 16))
        self._draw_wrapped(
            self.screen,
            self.fonts["small"],
            self.localizer.text("objective.explore"),
            theme.muted,
            pygame.Rect(visual.x + 20, visual.y + 46, visual.width - 40, 44),
            self.fonts["small"].get_linesize(),
        )
        plan = pygame.Rect(visual.x + 20, visual.y + 96, visual.width - 40, visual.height - 124)
        self._draw_card(plan, fill=theme.surface, border=theme.border, radius=theme.radius_medium, shadow=2)
        board = pygame.Rect(plan.x + 18, plan.y + 20, plan.width - 36, int(plan.height * 0.62))
        self._draw_card(board, fill=(247, 246, 241), border=theme.border, radius=theme.radius_medium, shadow=1)
        left_lane = pygame.Rect(board.x + 22, board.y + 20, int(board.width * 0.29), board.height - 40)
        right_lane = pygame.Rect(left_lane.right + 22, board.y + 20, int(board.width * 0.38), board.height - 40)
        hall = pygame.Rect(right_lane.right + 18, board.y + 20, board.right - (right_lane.right + 40), board.height - 40)
        for rect, label_key in (
            (left_lane, "building.library"),
            (right_lane, "building.student_center"),
            (hall, "building.campus"),
        ):
            pygame.draw.rect(self.screen, theme.paper_alt, rect, border_radius=18)
            pygame.draw.rect(self.screen, theme.border, rect, 2, border_radius=18)
            label = self.fonts["small"].render(self.localizer.text(label_key), True, theme.ink)
            self.screen.blit(label, (rect.x + 12, rect.y + 10))
        for y in range(board.y + 56, board.bottom - 26, 54):
            pygame.draw.line(self.screen, theme.info, (board.x + 22, y), (board.right - 22, y), 2)
        for rect in (
            pygame.Rect(left_lane.x + 18, left_lane.bottom - 54, left_lane.width - 36, 16),
            pygame.Rect(right_lane.x + 18, right_lane.y + 58, right_lane.width - 36, 16),
            pygame.Rect(hall.x + 14, hall.y + 70, hall.width - 28, 16),
        ):
            pygame.draw.rect(self.screen, theme.accent, rect, border_radius=8)
        briefing = pygame.Rect(plan.x + 18, board.bottom + 16, plan.width - 36, plan.bottom - board.bottom - 34)
        self._draw_card(briefing, fill=theme.paper_alt, border=theme.info, radius=theme.radius_small, shadow=1)
        guide_title = self.fonts["small"].render(self.localizer.text("ui.menu_briefing"), True, theme.warning)
        self.screen.blit(guide_title, (briefing.x + 16, briefing.y + 12))
        guide_copy = [
            self.localizer.text("ui.menu_step_1"),
            self.localizer.text("ui.menu_step_2"),
            self.localizer.text("ui.menu_step_3"),
        ]
        y = briefing.y + 34
        for line in guide_copy:
            self._draw_wrapped(
                self.screen,
                self.fonts["tiny"],
                line,
                theme.ink,
                pygame.Rect(briefing.x + 16, y, briefing.width - 32, 18),
                self.fonts["tiny"].get_linesize(),
            )
            y += 18

        rows = [
            ("menu.start", self.localizer.text("menu.start")),
            ("menu.mode", self.localizer.text(f"mode.{self.selected_mode}")),
            ("menu.language", self.localizer.text(f"lang.{self.selected_language}")),
            ("menu.spawn", self.localizer.text(f"spawn.{self.selected_spawn}")),
            ("menu.quit", self.localizer.text("menu.quit")),
        ]
        button_h = 68
        top = actions.y + 22
        for index, (label_key, value) in enumerate(rows):
            row_rect = pygame.Rect(actions.x + 18, top + index * (button_h + 14), actions.width - 36, button_h)
            field = self.menu_options[index]
            active = self.menu_index == index
            kind = "primary" if field == "start" else ("danger" if field == "quit" else "secondary")
            self._draw_button(row_rect, "", active=active, kind=kind, compact=True)
            label = self.fonts["tiny"].render(self.localizer.text(label_key), True, theme.muted if not active else theme.warning)
            value_surface = self.fonts["body"].render(value, True, theme.light_ink if kind == "primary" else theme.ink)
            self.screen.blit(label, (row_rect.x + 18, row_rect.y + 10))
            self.screen.blit(value_surface, (row_rect.x + 18, row_rect.y + 28))
            if field in {"mode", "language", "spawn"}:
                hint = self.fonts["tiny"].render("← →", True, theme.info)
                self.screen.blit(hint, hint.get_rect(midright=(row_rect.right - 18, row_rect.centery)))

        title_surface = self.fonts["heading"].render(self.localizer.text("ui.menu_controls"), True, theme.light_ink)
        self.screen.blit(title_surface, (help_rect.x + 18, help_rect.y + 18))
        help_lines = [
            self.localizer.text("menu.help"),
            self.localizer.text("ui.pause_exit_hint"),
            self.localizer.text("ui.log_hint"),
            self.localizer.text("ui.fullscreen_hint"),
        ]
        y = help_rect.y + 58
        for line in help_lines:
            pill = pygame.Rect(help_rect.x + 18, y, help_rect.width - 36, 44)
            self._draw_card(pill, fill=(theme.surface_alt[0], theme.surface_alt[1], theme.surface_alt[2], 232), border=theme.info, radius=theme.radius_small, shadow=1)
            self._draw_wrapped(
                self.screen,
                self.fonts["tiny"],
                line,
                theme.ink,
                pill.inflate(-16, -10),
                self.fonts["tiny"].get_linesize(),
            )
            y += 54
        status_card = pygame.Rect(help_rect.x + 18, help_rect.bottom - 108, help_rect.width - 36, 90)
        self._draw_card(status_card, fill=theme.dark_surface, border=theme.dark_border, radius=theme.radius_medium, shadow=2)
        status_title = self.fonts["tiny"].render(self.localizer.text("ui.menu_status"), True, theme.warning)
        self.screen.blit(status_title, (status_card.x + 14, status_card.y + 12))
        self._draw_wrapped(
            self.screen,
            self.fonts["tiny"],
            self.localizer.text("objective.explore"),
            theme.light_ink,
            pygame.Rect(status_card.x + 14, status_card.y + 32, status_card.width - 28, status_card.height - 42),
            self.fonts["tiny"].get_linesize(),
        )

    def _render_world(self) -> None:
        session = self.session
        assert session is not None
        scene = self._current_scene()
        theme = self.ui_theme
        offset_x, offset_y = self._camera_offset()
        base_color = pygame.Color(scene.theme_color)
        if self._high_contrast_enabled():
            base_color = pygame.Color(26, 42, 58)
        self.screen.fill(base_color)
        self._draw_grid(offset_x, offset_y)
        for room in scene.rooms:
            room_rect = pygame.Rect(room.x - offset_x, room.y - offset_y, room.width, room.height)
            self._draw_room_world(room, room_rect)
            label = self.fonts["tiny"].render(self.localizer.text(room.label_key), True, theme.ink)
            self.screen.blit(label, (room_rect.x + 8, room_rect.y + 8))
        prop_colors = {
            "bookshelf": (120, 72, 42),
            "desk_cluster": (151, 126, 89),
            "divider": (95, 113, 131),
            "service_desk": (87, 105, 124),
            "classroom_block": (124, 105, 148),
        }
        for prop in scene.props:
            rect = pygame.Rect(prop.x - offset_x, prop.y - offset_y, prop.width, prop.height)
            self._draw_prop_world(prop, rect)
        for collision in scene.collisions:
            rect = pygame.Rect(collision.x - offset_x, collision.y - offset_y, collision.width, collision.height)
            pygame.draw.rect(self.screen, (72, 86, 96), rect, border_radius=6)
        for zone in scene.exit_zones:
            rect = pygame.Rect(zone.x - offset_x, zone.y - offset_y, zone.width, zone.height)
            pygame.draw.rect(self.screen, theme.warning, rect, 2, border_radius=8)
            title = self.fonts["tiny"].render(self.localizer.text(zone.label_key), True, theme.warning)
            self.screen.blit(title, (rect.x + 6, rect.y - 16))
        if session.phase in {"Alert", "Shelter"}:
            for safe in scene.safe_areas:
                rect = pygame.Rect(safe.x - offset_x, safe.y - offset_y, safe.width, safe.height)
                pygame.draw.rect(self.screen, theme.success, rect, 3, border_radius=10)
            for risk in scene.risk_areas:
                rect = pygame.Rect(risk.x - offset_x, risk.y - offset_y, risk.width, risk.height)
                overlay = pygame.Surface((max(1, rect.width), max(1, rect.height)), pygame.SRCALPHA)
                overlay.fill((theme.danger[0], theme.danger[1], theme.danger[2], 52))
                self.screen.blit(overlay, rect.topleft)
                pygame.draw.rect(self.screen, theme.danger, rect, 2, border_radius=10)
        for board in scene.map_boards:
            rect = pygame.Rect(board.x - offset_x, board.y - offset_y, board.width, board.height)
            pole = pygame.Rect(rect.centerx - 4, rect.centery - 2, 8, 30)
            sign = pygame.Rect(rect.centerx - 18, rect.centery - 22, 36, 24)
            pygame.draw.rect(self.screen, (84, 70, 54), pole, border_radius=3)
            pygame.draw.rect(self.screen, theme.surface, sign, border_radius=6)
            pygame.draw.rect(self.screen, theme.warning, sign, 2, border_radius=6)
            icon = self.fonts["tiny"].render("MAP", True, theme.ink)
            self.screen.blit(icon, icon.get_rect(center=sign.center))
        for link in scene.links:
            rect = pygame.Rect(link.x - offset_x, link.y - offset_y, link.width, link.height)
            blocked = session.phase in {"Alert", "Shelter"} and link.id in session.blocked_links
            color = theme.danger if blocked else theme.info
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, theme.surface, rect.inflate(-10, -10), 1, border_radius=6)
        for interaction in self.content.interactions:
            if interaction.scene_id != scene.id:
                continue
            rect = pygame.Rect(interaction.x - offset_x, interaction.y - offset_y, interaction.width, interaction.height)
            pygame.draw.circle(self.screen, theme.surface, rect.center, 20)
            pygame.draw.circle(self.screen, theme.border, rect.center, 20, 2)
            unread = interaction.id not in session.interactions_used
            fill = theme.warning if unread else theme.surface_soft
            pygame.draw.circle(self.screen, fill, rect.center, 16)
            icon = self.fonts["tiny"].render(interaction.icon, True, theme.ink)
            self.screen.blit(icon, icon.get_rect(center=rect.center))
        for noise in self.noises:
            if noise.scene_id != scene.id:
                continue
            center = (int(noise.x - offset_x), int(noise.y - offset_y))
            radius = int(12 + (1.0 - min(1.0, noise.timer / 3.5)) * 40)
            pygame.draw.circle(self.screen, theme.warning, center, radius, 2)
        for runtime in self.actor_states.values():
            if runtime.scene_id != scene.id:
                continue
            center = (int(runtime.x - offset_x), int(runtime.y - offset_y))
            definition = self.actor_defs[runtime.id]
            self._draw_actor_world(runtime, definition, center)
            label_key = self.actor_defs[runtime.id].label_key
            if self.selected_mode == "practice" and label_key:
                label = self.fonts["tiny"].render(self.localizer.text(label_key), True, theme.light_ink)
                self.screen.blit(label, (center[0] - 44, center[1] - 28))
        player = (int(session.player_x - offset_x), int(session.player_y - offset_y))
        pygame.draw.circle(self.screen, theme.surface, player, 14)
        pygame.draw.circle(self.screen, theme.dark_surface, player, 14, 2)

    def _draw_grid(self, offset_x: int, offset_y: int) -> None:
        width, height = self.screen.get_size()
        grid = 32
        color = (56, 73, 90)
        start_x = -(offset_x % grid)
        start_y = -(offset_y % grid)
        for x in range(start_x, width, grid):
            pygame.draw.line(self.screen, color, (x, 0), (x, height), 1)
        for y in range(start_y, height, grid):
            pygame.draw.line(self.screen, color, (0, y), (width, y), 1)

    def _render_hud(self) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        layout = self._screen_layout()
        scene = self._current_scene()
        advisory = self._current_advisory()
        room = scene.room_at(session.player_x, session.player_y)
        room_text = self.localizer.text(room.label_key) if room else self.localizer.text("ui.room_unknown")
        self._draw_chip(
            layout.location_chip,
            self.localizer.text("ui.location"),
            f"{self.localizer.text(scene.floor_label_key)}\n{room_text}",
            tone="muted",
            icon="◎",
            compact=True,
        )

        required_clues = int(self.content.scenario.ending_conditions.get("required_clues", 3))
        self._draw_chip(
            layout.route_chip,
            f"{self.localizer.text('ui.advisor_header')} · {advisory.backend_label}",
            f"{advisory.headline}\n{advisory.route_label}: {advisory.route_value}",
            tone=advisory.tone,
            icon="↗",
            compact=True,
        )

        gate_reason = self._gate_exit_block_reason()
        if gate_reason:
            gate_line = self.localizer.text(gate_reason)
            gate_tone = "danger"
        else:
            gate_line = advisory.summary if session.current_wave_index >= 0 else self.localizer.text("objective.explore")
            gate_tone = "success" if session.scene_id == "outdoor_main" else "warning"
        pill_w = int((layout.status_bar.width - theme.small_gap * 2) / 3)
        pill_rects = [
            pygame.Rect(layout.status_bar.x + idx * (pill_w + theme.small_gap), layout.status_bar.y, pill_w, layout.status_bar.height)
            for idx in range(3)
        ]
        self._draw_stat_pill(pill_rects[0], self.localizer.text("ui.bottles"), str(session.bottles), tone="accent")
        self._draw_stat_pill(pill_rects[1], self.localizer.text("ui.clues"), f"{len(session.clues_found)}/{required_clues}", tone="info")
        survive_seconds = int(self.content.scenario.ending_conditions.get("survive_seconds", 420))
        remaining = max(0, survive_seconds - int(session.alert_elapsed))
        self._draw_stat_pill(pill_rects[2], self.localizer.text("ui.police_eta"), f"{remaining}s" if session.current_wave_index >= 0 else "--", tone="success")
        alert_rect = layout.alert_bar
        fill, border, _ = self._tone(gate_tone if session.current_wave_index >= 0 else "muted")
        self._draw_card(alert_rect, fill=(fill[0], fill[1], fill[2], 226), border=border, radius=theme.radius_medium, shadow=2)
        stripe = pygame.Rect(alert_rect.x + 12, alert_rect.y + 10, max(4, int(alert_rect.width * 0.34)), 5)
        pygame.draw.rect(self.screen, border, stripe, border_radius=3)
        phase_surface = self.fonts["small"].render(self.localizer.text(f"phase.{session.phase}"), True, theme.ink)
        self.screen.blit(phase_surface, (alert_rect.x + 16, alert_rect.y + 16))
        self._draw_wrapped(
            self.screen,
            self.fonts["tiny"],
            gate_line,
            theme.muted,
            pygame.Rect(alert_rect.x + 110, alert_rect.y + 18, alert_rect.width - 124, 18),
            self.fonts["tiny"].get_linesize(),
        )

        prompt = self.localizer.text("ui.current_prompt")
        exit_zone = self._current_exit_zone()
        nearest_interaction = self._nearest_interaction()
        nearest_link = self._nearest_link()
        nearest_robot = self._nearest_robot()
        if exit_zone:
            prompt = f"{self.localizer.text('ui.interact')}: {self.localizer.text(exit_zone.label_key)}"
        elif nearest_interaction:
            prompt = f"{self.localizer.text('ui.interact')}: {self.localizer.text(nearest_interaction.label_key)}"
        elif nearest_link:
            prompt = f"{self.localizer.text('ui.interact')}: {self.localizer.text(nearest_link.label_key)}"
        elif nearest_robot:
            label_key = self.actor_defs[nearest_robot.id].label_key
            prompt = f"{self.localizer.text('ui.interact')}: {self.localizer.text(label_key)}"
        elif self._can_open_map():
            prompt = self.localizer.text("ui.map_access_hint")
        prompt_text = f"{prompt}   |   {self.localizer.text('ui.pause_exit_hint')}"
        self._draw_card(layout.action_bar, fill=(theme.dark_surface[0], theme.dark_surface[1], theme.dark_surface[2], 236), border=theme.dark_border, radius=theme.radius_medium, shadow=4)
        self._draw_wrapped(self.screen, self.fonts["small"], prompt_text, theme.light_ink, layout.action_bar.inflate(-16, -12), self.fonts["small"].get_linesize())
        self._draw_card(layout.subtitles, fill=(theme.paper[0], theme.paper[1], theme.paper[2], 228), border=theme.border, radius=theme.radius_medium, shadow=4)
        subtitles_rect = layout.subtitles.inflate(-16, -14)
        header = self.fonts["tiny"].render(self.localizer.text("ui.subtitles_header"), True, theme.warning)
        self.screen.blit(header, (subtitles_rect.x, subtitles_rect.y))
        hint = self.fonts["tiny"].render(self.localizer.text("ui.log_hint"), True, theme.info)
        self.screen.blit(hint, hint.get_rect(topright=(subtitles_rect.right, subtitles_rect.y)))
        if self._subtitles_enabled():
            y = subtitles_rect.y + 20
            for title, body in session.subtitles[-2:]:
                card = pygame.Rect(subtitles_rect.x, y, subtitles_rect.width, 34)
                if card.bottom > subtitles_rect.bottom:
                    break
                self._draw_card(card, fill=(theme.surface_alt[0], theme.surface_alt[1], theme.surface_alt[2], 224), border=theme.info, radius=theme.radius_small, shadow=1)
                title_surface = self.fonts["tiny"].render(title, True, theme.ink)
                self.screen.blit(title_surface, (card.x + 10, card.y + 6))
                for line in self._wrap_text(self.fonts["tiny"], body, subtitles_rect.width)[:1]:
                    body_surface = self.fonts["tiny"].render(line, True, theme.muted)
                    self.screen.blit(body_surface, (card.x + 10, card.y + 18))
                y += 38
        else:
            self._draw_wrapped(self.screen, self.fonts["small"], self.localizer.text("ui.subtitles_off"), theme.muted, subtitles_rect, self.fonts["small"].get_linesize())

    def _render_overlays(self) -> None:
        session = self.session
        assert session is not None
        layout = self._screen_layout()
        self.pause_buttons = []
        if session.opening_active:
            self._draw_modal(layout.modal, self.localizer.text("ui.opening_title"), eyebrow=self.localizer.text("ui.modal_eyebrow.opening"))
            self._render_opening(layout.modal_body)
            return
        if session.outcome:
            title_key = "debrief.title.success" if session.outcome == "success" else "debrief.title.fail"
            self._draw_modal(layout.modal, self.localizer.text(title_key), eyebrow=self.localizer.text("ui.modal_eyebrow.debrief"))
            self._render_debrief(layout.modal_body)
            return
        if session.paused:
            self._draw_modal(layout.modal, self.localizer.text("ui.pause_title"), eyebrow=self.localizer.text("ui.modal_eyebrow.pause"))
            self._render_pause(layout.modal_body)
            return
        if session.map_open:
            self._draw_modal(layout.modal, self.localizer.text("ui.map_title"), eyebrow=self.localizer.text("ui.modal_eyebrow.map"))
            self._render_map(layout.modal_body)
            return
        if session.phone_open:
            self._draw_modal(layout.modal, self.localizer.text("ui.phone_title"), eyebrow=self.localizer.text("ui.modal_eyebrow.phone"))
            self._render_phone(layout.modal_body)
            return
        if session.log_open:
            self._draw_modal(layout.modal, self.localizer.text("ui.log_title"), eyebrow=self.localizer.text("ui.modal_eyebrow.log"))
            self._render_log(layout.modal_body)

    def _render_opening(self, rect: pygame.Rect) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        beats = self.content.scenario.opening_sequence
        beat = beats[min(session.opening_index, len(beats) - 1)]
        left, right = split_columns(rect, 0.62, theme.gap)
        self._draw_card(left, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=4)
        self._draw_card(right, fill=theme.paper_alt, border=theme.border, radius=theme.radius_large, shadow=4)
        tag = self.fonts["tiny"].render(f"STEP {session.opening_index + 1}/{len(beats)}", True, theme.info)
        self.screen.blit(tag, (left.x + 18, left.y + 18))
        self._draw_wrapped(self.screen, self.fonts["title"], self.localizer.text(beat.title_key), theme.ink, pygame.Rect(left.x + 18, left.y + 42, left.width - 36, 72), self.fonts["title"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["body"], self.localizer.text(beat.body_key), theme.muted, pygame.Rect(left.x + 18, left.y + 112, left.width - 36, left.height - 154), self.fonts["body"].get_linesize())
        footer = self.fonts["small"].render(self.localizer.text("ui.opening_hint"), True, theme.warning)
        self.screen.blit(footer, (left.x + 18, left.bottom - 28))

        guide_title = self.fonts["heading"].render(self.localizer.text("ui.opening_route_preview"), True, theme.ink)
        self.screen.blit(guide_title, (right.x + 18, right.y + 18))
        checkpoints = [
            (self.localizer.text("ui.opening_preview_map"), self.localizer.text("ui.opening_copy_map")),
            (self.localizer.text("ui.opening_preview_notice"), self.localizer.text("ui.opening_copy_notice")),
            (self.localizer.text("ui.opening_preview_safe"), self.localizer.text("ui.opening_copy_safe")),
        ]
        y = right.y + 64
        for index, (heading, body) in enumerate(checkpoints):
            card = pygame.Rect(right.x + 18, y, right.width - 36, 84)
            self._draw_card(card, fill=theme.surface, border=theme.info, radius=theme.radius_medium, shadow=1)
            num = self.fonts["heading"].render(str(index + 1), True, theme.warning)
            self.screen.blit(num, (card.x + 14, card.y + 10))
            heading_surface = self.fonts["small"].render(heading, True, theme.ink)
            self.screen.blit(heading_surface, (card.x + 56, card.y + 12))
            self._draw_wrapped(self.screen, self.fonts["tiny"], body, theme.muted, pygame.Rect(card.x + 56, card.y + 34, card.width - 70, 38), self.fonts["tiny"].get_linesize())
            y += 96

    def _render_phone(self, rect: pygame.Rect) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        advisory = self._current_advisory()
        left, right = split_columns(rect, 0.58, theme.gap)
        self._draw_card(left, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=3)
        self._draw_card(right, fill=theme.paper_alt, border=theme.border, radius=theme.radius_large, shadow=3)
        y = left.y + 16
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.phone_updates"), theme.ink, pygame.Rect(left.x + 16, y, left.width - 32, 26), self.fonts["heading"].get_linesize())
        y += 34
        if not session.alert_history:
            self._draw_wrapped(self.screen, self.fonts["tiny"], self.localizer.text("ui.no_updates"), theme.muted, pygame.Rect(left.x + 16, y, left.width - 32, 20), self.fonts["tiny"].get_linesize())
        else:
            entries = session.alert_history[-5:]
            for idx, (title, body) in enumerate(entries):
                card = pygame.Rect(left.x + 14, y, left.width - 28, 78)
                tone = "danger" if idx == len(entries) - 1 else "info"
                fill, border, _ = self._tone(tone)
                self._draw_card(card, fill=fill, border=border, radius=theme.radius_medium, shadow=2)
                line = pygame.Rect(card.x + 14, card.y + 14, 4, card.height - 28)
                pygame.draw.rect(self.screen, border, line, border_radius=2)
                self._draw_wrapped(self.screen, self.fonts["small"], title, theme.ink, pygame.Rect(card.x + 30, card.y + 10, card.width - 44, 22), self.fonts["small"].get_linesize())
                self._draw_wrapped(self.screen, self.fonts["tiny"], body, theme.muted, pygame.Rect(card.x + 30, card.y + 34, card.width - 44, 34), self.fonts["tiny"].get_linesize())
                y += 90

        right_inner = pygame.Rect(right.x, right.y, right.width, right.height)
        top_heights = [min(136, max(110, int(right_inner.height * 0.22))), min(84, max(70, int(right_inner.height * 0.13))), min(84, max(70, int(right_inner.height * 0.13)))]
        remaining = right_inner.height - sum(top_heights) - theme.gap * 3
        if remaining < 120:
            deficit = 120 - remaining
            top_heights[0] = max(84, top_heights[0] - deficit // 3)
            top_heights[1] = max(68, top_heights[1] - deficit // 3)
            top_heights[2] = max(68, top_heights[2] - deficit // 3)
            remaining = right_inner.height - sum(top_heights) - theme.gap * 3
        panels = stack_rows(right_inner, [top_heights[0], top_heights[1], top_heights[2], max(120, remaining)], theme.gap)
        for panel in panels:
            self._draw_card(panel, fill=theme.surface, border=theme.border, radius=theme.radius_medium, shadow=1)

        y2 = panels[0].y + 14
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.phone_clues"), theme.ink, pygame.Rect(panels[0].x + 14, y2, panels[0].width - 28, 22), self.fonts["heading"].get_linesize())
        y2 += 30
        required = int(self.content.scenario.ending_conditions.get("required_clues", 3))
        clue_line = f"{self.localizer.text('ui.clues')}: {len(session.clues_found)}/{required}"
        self._draw_wrapped(self.screen, self.fonts["small"], clue_line, theme.info, pygame.Rect(panels[0].x + 14, y2, panels[0].width - 28, 20), self.fonts["small"].get_linesize())
        y2 += 18
        clue_ids = sorted(session.clues_found)
        for clue_id in clue_ids[:4]:
            interaction = next((item for item in self.content.interactions if item.id == clue_id), None)
            if interaction is None:
                continue
            self._draw_wrapped(self.screen, self.fonts["tiny"], f"• {self.localizer.text(interaction.label_key)}", theme.muted, pygame.Rect(panels[0].x + 14, y2, panels[0].width - 28, 18), self.fonts["tiny"].get_linesize())
            y2 += 16
        if len(clue_ids) > 4:
            self._draw_wrapped(
                self.screen,
                self.fonts["tiny"],
                self.localizer.text("ui.more_items"),
                theme.info,
                pygame.Rect(panels[0].x + 14, y2, panels[0].width - 28, 18),
                self.fonts["tiny"].get_linesize(),
                max_lines=1,
                ellipsis=True,
            )
        self._draw_chip(panels[1], self.localizer.text("ui.phase"), self.localizer.text(f"phase.{session.phase}"), tone="warning", icon="⌁", compact=True)
        info = f"{self.localizer.text('ui.bottles')}: {session.bottles}"
        self._draw_chip(panels[2], self.localizer.text("ui.bottles"), info, tone="accent", icon="◉", compact=True)
        latest_title, latest_body = session.alert_history[-1] if session.alert_history else (self.localizer.text("ui.no_updates"), self.localizer.text("ui.read_alert_hint"))
        bottom_left, bottom_right = split_columns(panels[3], 0.52, theme.small_gap)
        self._draw_card(bottom_left, fill=theme.paper, border=theme.info, radius=theme.radius_small, shadow=0)
        self._draw_card(bottom_right, fill=theme.paper, border=theme.border, radius=theme.radius_small, shadow=0)
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.advisor_header"), theme.ink, pygame.Rect(bottom_left.x + 14, bottom_left.y + 14, bottom_left.width - 28, 22), self.fonts["heading"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["small"], advisory.headline, theme.ink, pygame.Rect(bottom_left.x + 14, bottom_left.y + 42, bottom_left.width - 28, 32), self.fonts["small"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], advisory.detail, theme.muted, pygame.Rect(bottom_left.x + 14, bottom_left.y + 76, bottom_left.width - 28, bottom_left.height - 92), self.fonts["tiny"].get_linesize())
        model_badge = pygame.Rect(bottom_left.x + 14, bottom_left.bottom - 34, bottom_left.width - 28, 22)
        self._draw_card(model_badge, fill=theme.surface_alt, border=theme.warning, radius=theme.radius_small, shadow=0)
        self._draw_wrapped(self.screen, self.fonts["tiny"], f"{self.localizer.text('ui.advisor_backend')}: {advisory.backend_label}", theme.ink, model_badge.inflate(-10, -4), self.fonts["tiny"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.phone_latest"), theme.ink, pygame.Rect(bottom_right.x + 14, bottom_right.y + 14, bottom_right.width - 28, 22), self.fonts["heading"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["small"], latest_title, theme.ink, pygame.Rect(bottom_right.x + 14, bottom_right.y + 42, bottom_right.width - 28, 30), self.fonts["small"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], latest_body, theme.muted, pygame.Rect(bottom_right.x + 14, bottom_right.y + 72, bottom_right.width - 28, bottom_right.height - 86), self.fonts["tiny"].get_linesize())

    def _render_map(self, rect: pygame.Rect) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        scene = self._current_scene()
        advisory = self._current_advisory()
        left, right = split_columns(rect, 0.71, theme.gap)
        self._draw_card(left, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=3)
        self._draw_card(right, fill=theme.paper_alt, border=theme.border, radius=theme.radius_large, shadow=3)

        title = self.fonts["heading"].render(self.localizer.text("ui.map_local_plan"), True, theme.ink)
        self.screen.blit(title, (left.x + 16, left.y + 14))
        sub = self.fonts["small"].render(f"{self.localizer.text(scene.building_key)} / {self.localizer.text(scene.floor_label_key)}", True, theme.info)
        self.screen.blit(sub, (left.x + 16, left.y + 42))
        tabs_rect = pygame.Rect(left.x + 16, left.y + 74, left.width - 32, 36)
        self._draw_floor_tabs(tabs_rect, scene)
        plan_rect = pygame.Rect(left.x + 16, tabs_rect.bottom + 12, left.width - 32, left.bottom - tabs_rect.bottom - 28)

        padding = 16
        draw_area = plan_rect.inflate(-padding * 2, -padding * 2)
        scale = min(draw_area.width / scene.width, draw_area.height / scene.height)
        scaled_w = int(scene.width * scale)
        scaled_h = int(scene.height * scale)
        origin_x = draw_area.x + (draw_area.width - scaled_w) // 2
        origin_y = draw_area.y + (draw_area.height - scaled_h) // 2
        blueprint_rect = pygame.Rect(origin_x, origin_y, max(2, scaled_w), max(2, scaled_h))
        pygame.draw.rect(self.screen, (248, 246, 241), blueprint_rect, border_radius=12)
        pygame.draw.rect(self.screen, theme.border, blueprint_rect, 2, border_radius=12)

        def scale_rect(x: int, y: int, w: int, h: int) -> pygame.Rect:
            rect_x = origin_x + int(x * scale)
            rect_y = origin_y + int(y * scale)
            rect_w = max(2, int(w * scale))
            rect_h = max(2, int(h * scale))
            return pygame.Rect(rect_x, rect_y, rect_w, rect_h)

        for room in scene.rooms:
            room_rect = scale_rect(room.x, room.y, room.width, room.height)
            pygame.draw.rect(self.screen, (224, 230, 232), room_rect, border_radius=6)
            pygame.draw.rect(self.screen, theme.border, room_rect, 1, border_radius=6)
            if room_rect.width > 70 and room_rect.height > 28:
                label = self.fonts["tiny"].render(self.localizer.text(room.label_key), True, theme.ink)
                self.screen.blit(label, (room_rect.x + 4, room_rect.y + 2))

        for prop in scene.props:
            prop_rect = scale_rect(prop.x, prop.y, prop.width, prop.height)
            fill = (133, 92, 58) if prop.solid else (111, 131, 146)
            pygame.draw.rect(self.screen, fill, prop_rect, border_radius=3)
            pygame.draw.rect(self.screen, theme.surface, prop_rect, 1, border_radius=3)

        for safe in scene.safe_areas:
            safe_rect = scale_rect(safe.x, safe.y, safe.width, safe.height)
            pygame.draw.rect(self.screen, theme.success, safe_rect, 2, border_radius=4)
        for risk in scene.risk_areas:
            risk_rect = scale_rect(risk.x, risk.y, risk.width, risk.height)
            overlay = pygame.Surface((max(1, risk_rect.width), max(1, risk_rect.height)), pygame.SRCALPHA)
            overlay.fill((theme.danger[0], theme.danger[1], theme.danger[2], 50))
            self.screen.blit(overlay, risk_rect.topleft)
            pygame.draw.rect(self.screen, theme.danger, risk_rect, 2, border_radius=4)

        for link in scene.links:
            link_rect = scale_rect(link.x, link.y, link.width, link.height)
            blocked = session.phase in {"Alert", "Shelter"} and (link.id in session.blocked_links or link.locked_on_alert)
            color = theme.danger if blocked else theme.info
            pygame.draw.rect(self.screen, color, link_rect, border_radius=3)

        for zone in scene.exit_zones:
            if not phase_allows(session.phase, zone.state_rules):
                continue
            zone_rect = scale_rect(zone.x, zone.y, zone.width, zone.height)
            pygame.draw.rect(self.screen, theme.warning, zone_rect, 2, border_radius=4)

        px = origin_x + int(session.player_x * scale)
        py = origin_y + int(session.player_y * scale)
        pygame.draw.circle(self.screen, theme.dark_surface, (px, py), 8)
        pygame.draw.circle(self.screen, theme.warning, (px, py), 8, 2)
        marker = self.fonts["tiny"].render(self.localizer.text("ui.you_are_here"), True, theme.warning)
        self.screen.blit(marker, (px + 10, py - 8))

        room = scene.room_at(session.player_x, session.player_y)
        right_inner = right.inflate(-16, -16)
        info_h = 112
        route_h = 186
        links_h = 92
        legend_h = max(116, right_inner.height - info_h - route_h - links_h - theme.gap * 3)
        info_panel, route_panel, links_panel, legend_panel = stack_rows(right_inner, [info_h, route_h, links_h, legend_h], theme.gap)
        for panel in (info_panel, route_panel, links_panel, legend_panel):
            self._draw_card(panel, fill=theme.surface, border=theme.border, radius=theme.radius_medium, shadow=1)
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.location"), theme.ink, pygame.Rect(info_panel.x + 14, info_panel.y + 14, info_panel.width - 28, 24), self.fonts["heading"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], f"{self.localizer.text('ui.building')}: {self.localizer.text(scene.building_key)}", theme.muted, pygame.Rect(info_panel.x + 14, info_panel.y + 44, info_panel.width - 28, 18), self.fonts["tiny"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], f"{self.localizer.text('ui.floor')}: {self.localizer.text(scene.floor_label_key)}", theme.muted, pygame.Rect(info_panel.x + 14, info_panel.y + 62, info_panel.width - 28, 18), self.fonts["tiny"].get_linesize())
        room_text = self.localizer.text(room.label_key) if room else self.localizer.text("ui.room_unknown")
        self._draw_wrapped(self.screen, self.fonts["small"], f"{self.localizer.text('ui.room')}: {room_text}", theme.ink, pygame.Rect(info_panel.x + 14, info_panel.y + 84, info_panel.width - 28, 22), self.fonts["small"].get_linesize())

        y = route_panel.y + 14
        gate_route, gate_route_key = self._route_to_scene_labels("outdoor_main")
        secret_route, secret_route_key = self._route_to_scene_labels("library_f2")
        gate_route_text = (
            self.localizer.text("ui.map_route_current_scene")
            if session.scene_id == "outdoor_main"
            else (" -> ".join(gate_route) if gate_route else self.localizer.text("ui.map_route_unknown"))
        )
        secret_route_text = (
            self.localizer.text("ui.map_route_current_scene")
            if session.scene_id == "library_f2"
            else (" -> ".join(secret_route) if secret_route else self.localizer.text("ui.map_route_unknown"))
        )
        gate_reason_key = self._gate_exit_block_reason()
        if gate_reason_key is None and session.scene_id == "outdoor_main":
            gate_status_text = self.localizer.text("ui.map_gate_status_open")
        elif gate_reason_key is None:
            gate_status_text = self.localizer.text("ui.map_gate_status_move")
        else:
            gate_status_text = f"{self.localizer.text('ui.map_gate_status_blocked')}: {self.localizer.text(gate_reason_key)}"
        required_clues = int(self.content.scenario.ending_conditions.get("required_clues", 3))
        if len(session.clues_found) >= required_clues:
            secret_status_text = self.localizer.text("ui.map_secret_status_open")
        else:
            secret_status_text = (
                f"{self.localizer.text('ui.map_secret_status_locked')} "
                f"{len(session.clues_found)}/{required_clues}"
            )
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.map_routes"), theme.ink, pygame.Rect(route_panel.x + 14, y, route_panel.width - 28, 22), self.fonts["heading"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], f"{self.localizer.text('ui.advisor_backend')}: {advisory.backend_label}", theme.info, pygame.Rect(route_panel.x + 14, y + 20, route_panel.width - 28, 18), self.fonts["tiny"].get_linesize())
        y += 22
        route_cards = [
            (self.localizer.text("ui.map_route_gate"), self.localizer.text(gate_route_key), gate_route_text, gate_status_text, theme.danger if gate_reason_key else theme.success),
            (self.localizer.text("ui.map_route_secret"), self.localizer.text(secret_route_key), secret_route_text, secret_status_text, theme.success if len(session.clues_found) >= required_clues else theme.danger),
        ]
        for title_text, state_text, route_copy, status_copy, color in route_cards:
            card = pygame.Rect(route_panel.x + 14, y + 14, route_panel.width - 28, 66)
            self._draw_card(card, fill=theme.paper_alt, border=color, radius=theme.radius_small, shadow=1)
            self._draw_wrapped(self.screen, self.fonts["tiny"], f"{title_text} ({state_text})", theme.ink, pygame.Rect(card.x + 10, card.y + 8, card.width - 20, 18), self.fonts["tiny"].get_linesize())
            self._draw_wrapped(self.screen, self.fonts["tiny"], route_copy, theme.muted, pygame.Rect(card.x + 10, card.y + 24, card.width - 20, 18), self.fonts["tiny"].get_linesize())
            self._draw_wrapped(self.screen, self.fonts["tiny"], status_copy, color, pygame.Rect(card.x + 10, card.y + 42, card.width - 20, 16), self.fonts["tiny"].get_linesize())
            y += 80

        y = links_panel.y + 14
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.map_links"), theme.ink, pygame.Rect(links_panel.x + 14, y, links_panel.width - 28, 22), self.fonts["heading"].get_linesize())
        y += 24
        for link in scene.links[:6]:
            target_scene = self.content.scene_by_id(link.target_scene_id)
            if target_scene is None:
                continue
            blocked = session.phase in {"Alert", "Shelter"} and (link.id in session.blocked_links or link.locked_on_alert)
            state_key = "ui.map_exit_status_locked" if blocked else "ui.map_exit_status_open"
            line = (
                f"• {self.localizer.text(target_scene.building_key)} / "
                f"{self.localizer.text(target_scene.floor_label_key)} ({self.localizer.text(state_key)})"
            )
            color = theme.danger if blocked else theme.muted
            self._draw_wrapped(
                self.screen,
                self.fonts["tiny"],
                line,
                color,
                pygame.Rect(links_panel.x + 14, y, links_panel.width - 28, 18),
                self.fonts["tiny"].get_linesize(),
                max_lines=1,
                ellipsis=True,
            )
            y += 18

        y = legend_panel.y + 14
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.map_legend"), theme.ink, pygame.Rect(legend_panel.x + 14, y, legend_panel.width - 28, 22), self.fonts["heading"].get_linesize())
        y += 28
        legend_rows = [
            (theme.surface_alt, "ui.map_legend_room"),
            ((133, 92, 58), "ui.map_legend_prop"),
            (theme.success, "ui.map_legend_safe"),
            (theme.danger, "ui.map_legend_risk"),
            (theme.info, "ui.map_legend_link"),
            (theme.warning, "ui.map_legend_exit"),
            (theme.dark_surface, "ui.map_legend_player"),
        ]
        for index, (color, key) in enumerate(legend_rows):
            col_x = legend_panel.x + 14 if index % 2 == 0 else legend_panel.centerx + 8
            row_y = y + (index // 2) * 22
            swatch = pygame.Rect(col_x, row_y + 3, 12, 12)
            pygame.draw.rect(self.screen, color, swatch, border_radius=3)
            self._draw_wrapped(
                self.screen,
                self.fonts["tiny"],
                self.localizer.text(key),
                theme.muted,
                pygame.Rect(col_x + 20, row_y, legend_panel.width // 2 - 28, 18),
                self.fonts["tiny"].get_linesize(),
                max_lines=1,
                ellipsis=True,
            )

    def _render_log(self, rect: pygame.Rect) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        header = pygame.Rect(rect.x, rect.y, rect.width, 34)
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.log_controls"), theme.ink, header, self.fonts["heading"].get_linesize())
        entries = list(reversed(session.message_history))
        if not entries:
            self._draw_wrapped(self.screen, self.fonts["small"], self.localizer.text("ui.log_empty"), theme.muted, pygame.Rect(rect.x, rect.y + 46, rect.width, 28), self.fonts["small"].get_linesize())
            return
        start = min(session.log_scroll, max(0, len(entries) - 1))
        visible = entries[start : start + 6]
        y = rect.y + 54
        colors = {"alert": theme.danger, "learning": theme.warning, "system": theme.info}
        timeline_x = rect.x + 22
        pygame.draw.line(self.screen, theme.border, (timeline_x, y), (timeline_x, rect.bottom - 18), 2)
        for kind, title, body in visible:
            card = pygame.Rect(rect.x + 42, y, rect.width - 54, 84)
            tone = colors.get(kind, theme.info)
            self._draw_card(card, fill=theme.surface, border=tone, radius=theme.radius_medium, shadow=2)
            pygame.draw.circle(self.screen, tone, (timeline_x, card.y + 20), 7)
            pill = pygame.Rect(card.x + 12, card.y + 10, 88, 20)
            pygame.draw.rect(self.screen, tone, pill, border_radius=10)
            kind_surface = self.fonts["tiny"].render(self.localizer.text(f"ui.log_kind.{kind}"), True, theme.surface)
            self.screen.blit(kind_surface, kind_surface.get_rect(center=pill.center))
            title_surface = self.fonts["small"].render(title, True, theme.ink)
            self.screen.blit(title_surface, (card.x + 112, card.y + 10))
            self._draw_wrapped(self.screen, self.fonts["tiny"], body, theme.muted, pygame.Rect(card.x + 12, card.y + 36, card.width - 24, 38), self.fonts["tiny"].get_linesize())
            y += 96
        if len(entries) > 6:
            ratio = min(1.0, (start + len(visible)) / len(entries))
            track = pygame.Rect(rect.right - 8, rect.y + 48, 4, rect.height - 62)
            pygame.draw.rect(self.screen, theme.surface_soft, track, border_radius=2)
            thumb_h = max(24, int(track.height * max(0.2, len(visible) / len(entries))))
            thumb_y = track.y + int((track.height - thumb_h) * ratio) - thumb_h
            thumb = pygame.Rect(track.x, max(track.y, min(track.bottom - thumb_h, thumb_y)), 4, thumb_h)
            pygame.draw.rect(self.screen, theme.info, thumb, border_radius=2)

    def _render_pause(self, rect: pygame.Rect) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        self.pause_buttons = []
        advisory = self._current_advisory()
        scene = self._current_scene()
        left, right = split_columns(rect, 0.56, theme.gap)
        self._draw_card(left, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=3)
        self._draw_card(right, fill=theme.paper_alt, border=theme.border, radius=theme.radius_large, shadow=3)
        help_card = pygame.Rect(left.x + 16, left.y + 16, left.width - 32, 60)
        self._draw_card(help_card, fill=theme.surface, border=theme.info, radius=theme.radius_small, shadow=1)
        self._draw_wrapped(
            self.screen,
            self.fonts["small"],
            self.localizer.text("ui.pause_help"),
            theme.ink,
            help_card.inflate(-14, -10),
            self.fonts["small"].get_linesize(),
            max_lines=2,
            ellipsis=True,
        )
        actions_y = help_card.bottom + 16
        primary_actions = [("resume", "ui.pause_resume"), ("menu", "ui.pause_return_menu"), ("quit", "ui.pause_quit_game")]
        for index, (action, key) in enumerate(primary_actions):
            label = self.localizer.text(key)
            button_rect = pygame.Rect(left.x + 16, actions_y + index * 62, left.width - 32, 50)
            kind = "primary" if action == "resume" else ("danger" if action == "quit" else "secondary")
            self._draw_button(button_rect, label, active=session.pause_selection == index, kind=kind)
            self.pause_buttons.append((button_rect, action))

        settings_top = actions_y + len(primary_actions) * 62 + 14
        available = left.bottom - 18 - settings_top
        settings = [
            ("ui.setting_language", self.localizer.text(f"lang.{self.selected_language}")),
            ("ui.setting_subtitles", self.localizer.text("ui.on") if self._subtitles_enabled() else self.localizer.text("ui.off")),
            ("ui.setting_high_contrast", self.localizer.text("ui.on") if self._high_contrast_enabled() else self.localizer.text("ui.off")),
            ("ui.setting_fullscreen", self.localizer.text("ui.on") if self.fullscreen else self.localizer.text("ui.off")),
            ("ui.setting_log", self.localizer.text("ui.available")),
        ]
        row_height = 34
        row_gap = max(6, min(10, int((available - row_height * len(settings)) / max(1, len(settings) - 1))))
        for row_index, (key, value) in enumerate(settings):
            row_y = settings_top + row_index * (row_height + row_gap)
            row = pygame.Rect(left.x + 16, row_y, left.width - 32, row_height)
            self._draw_card(row, fill=theme.surface_alt, border=theme.border, radius=theme.radius_small, shadow=1)
            label = self.fonts["tiny"].render(self.localizer.text(key), True, theme.ink)
            val = self.fonts["tiny"].render(value, True, theme.info)
            self.screen.blit(label, (row.x + 12, row.y + 8))
            self.screen.blit(val, val.get_rect(midright=(row.right - 12, row.centery)))

        summary_card = pygame.Rect(right.x + 16, right.y + 16, right.width - 32, 118)
        self._draw_card(summary_card, fill=theme.surface, border=theme.info, radius=theme.radius_medium, shadow=1)
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.pause_system_status"), theme.ink, pygame.Rect(summary_card.x + 14, summary_card.y + 14, summary_card.width - 28, 22), self.fonts["heading"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], f"{self.localizer.text('ui.location')}: {self.localizer.text(scene.floor_label_key)}", theme.muted, pygame.Rect(summary_card.x + 14, summary_card.y + 44, summary_card.width - 28, 18), self.fonts["tiny"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], f"{self.localizer.text('ui.advisor_backend')}: {advisory.backend_label}", theme.muted, pygame.Rect(summary_card.x + 14, summary_card.y + 62, summary_card.width - 28, 18), self.fonts["tiny"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["small"], advisory.headline, theme.ink, pygame.Rect(summary_card.x + 14, summary_card.y + 82, summary_card.width - 28, 24), self.fonts["small"].get_linesize())
        y_right = summary_card.bottom + 18
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.pause_hotkeys"), theme.ink, pygame.Rect(right.x + 16, y_right, right.width - 32, 22), self.fonts["heading"].get_linesize())
        y_right += 30
        for key, hotkey in self.pause_hint_lines:
            line = f"{hotkey}: {self.localizer.text(key)}"
            pill = pygame.Rect(right.x + 16, y_right, right.width - 32, 36)
            self._draw_card(pill, fill=theme.surface, border=theme.border, radius=theme.radius_small, shadow=1)
            self._draw_wrapped(self.screen, self.fonts["tiny"], line, theme.muted, pill.inflate(-12, -8), self.fonts["tiny"].get_linesize())
            y_right += 44
        hint_rect = pygame.Rect(right.x + 16, right.bottom - 42, right.width - 32, 28)
        self._draw_wrapped(self.screen, self.fonts["small"], self.localizer.text("ui.pause_focus_hint"), theme.info, hint_rect, self.fonts["small"].get_linesize())

    def _render_debrief(self, rect: pygame.Rect) -> None:
        session = self.session
        assert session is not None
        theme = self.ui_theme
        result_key = session.outcome_key or "success.police_arrival"
        left, right = split_columns(rect, 0.54, theme.gap)
        self._draw_card(left, fill=theme.surface, border=theme.border, radius=theme.radius_large, shadow=4)
        self._draw_card(right, fill=theme.surface_alt, border=theme.border, radius=theme.radius_large, shadow=4)
        summary = pygame.Rect(left.x + 14, left.y + 14, left.width - 28, 112)
        self._draw_card(summary, fill=theme.dark_surface, border=theme.dark_border, radius=theme.radius_medium, shadow=2)
        total_score = session.score.total()
        self._draw_wrapped(self.screen, self.fonts["tiny"], self.localizer.text("debrief.subtitle"), (219, 229, 236), pygame.Rect(summary.x + 16, summary.y + 14, summary.width - 32, 18), self.fonts["tiny"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text(result_key), theme.light_ink, pygame.Rect(summary.x + 16, summary.y + 38, summary.width - 32, 28), self.fonts["heading"].get_linesize())
        score_surface = self.fonts["display"].render(str(total_score), True, theme.warning)
        self.screen.blit(score_surface, score_surface.get_rect(topright=(summary.right - 18, summary.y + 18)))
        score_label = self.fonts["tiny"].render("/ 100", True, (219, 229, 236))
        self.screen.blit(score_label, score_label.get_rect(topright=(summary.right - 22, summary.y + 72)))
        y = summary.bottom + 18
        for category, label_key in (
            ("space_choice", "debrief.category.space_choice"),
            ("official_info", "debrief.category.official_info"),
            ("situational_awareness", "debrief.category.situational_awareness"),
            ("low_risk_assist", "debrief.category.low_risk_assist"),
            ("knowledge_collection", "debrief.category.knowledge_collection"),
        ):
            line = f"{self.localizer.text(label_key)}   {session.score.values[category]}/{SCORE_LIMITS[category]}"
            self._draw_wrapped(self.screen, self.fonts["small"], line, theme.ink, pygame.Rect(left.x + 18, y, left.width - 36, 18), self.fonts["small"].get_linesize())
            progress_track = pygame.Rect(left.x + 18, y + 24, left.width - 36, 10)
            ratio = max(0.0, min(1.0, session.score.values[category] / SCORE_LIMITS[category]))
            self._draw_progress_bar(progress_track, ratio, tone="accent")
            y += 48
        feedback = build_debrief_feedback_keys(
            ending=session.ending_type,
            captured=session.captured,
            clues=len(session.clues_found),
            bottle_throws=session.bottle_throws,
            alerts_ignored=session.ignored_alerts,
            safe_seconds=session.safe_seconds,
        )
        y_right = right.y + 16
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.debrief_feedback"), theme.ink, pygame.Rect(right.x + 14, y_right, right.width - 28, 22), self.fonts["heading"].get_linesize())
        y_right += 28
        for key in feedback[:5]:
            card = pygame.Rect(right.x + 14, y_right, right.width - 28, 46)
            self._draw_card(card, fill=theme.surface, border=theme.border, radius=theme.radius_small, shadow=1)
            self._draw_wrapped(self.screen, self.fonts["tiny"], f"• {self.localizer.text(key)}", theme.muted, card.inflate(-12, -10), self.fonts["tiny"].get_linesize())
            y_right += 54
        y_right += 10
        self._draw_wrapped(self.screen, self.fonts["heading"], self.localizer.text("ui.debrief_notes"), theme.ink, pygame.Rect(right.x + 14, y_right, right.width - 28, 22), self.fonts["heading"].get_linesize())
        y_right += 28
        for note in self.content.scenario.debrief_notes[:3]:
            self._draw_wrapped(self.screen, self.fonts["tiny"], f"• {self.localizer.text(note)}", theme.muted, pygame.Rect(right.x + 14, y_right, right.width - 28, 20), self.fonts["tiny"].get_linesize())
            y_right += 18
        metrics_card = pygame.Rect(left.x + 18, left.bottom - 146, left.width - 36, 88)
        self._draw_card(metrics_card, fill=theme.surface, border=theme.info, radius=theme.radius_small, shadow=1)
        stats = [
            f"{self.localizer.text('ui.clues')}: {len(session.clues_found)}",
            f"{self.localizer.text('ui.bottles')}: {session.bottle_throws}",
            f"{self.localizer.text('ui.safe_seconds')}: {int(session.safe_seconds)}s",
            f"{self.localizer.text('ui.ignored_alerts')}: {session.ignored_alerts}",
        ]
        for index, line in enumerate(stats):
            col_x = metrics_card.x + 14 if index % 2 == 0 else metrics_card.centerx + 8
            row_y = metrics_card.y + 14 + (index // 2) * 24
            self._draw_wrapped(
                self.screen,
                self.fonts["tiny"],
                line,
                theme.muted,
                pygame.Rect(col_x, row_y, metrics_card.width // 2 - 22, 18),
                self.fonts["tiny"].get_linesize(),
                max_lines=1,
                ellipsis=True,
            )
        footer = self.fonts["small"].render(self.localizer.text("ui.debrief_footer"), True, theme.warning)
        self.screen.blit(footer, (left.x + 18, left.bottom - 28))

    def _draw_backdrop(self) -> None:
        theme = self.ui_theme
        width, height = self.screen.get_size()
        top = pygame.Color(*theme.canvas_top)
        bottom = pygame.Color(*theme.canvas_bottom)
        for y in range(height):
            t = y / max(1, height - 1)
            color = (
                int(top.r + (bottom.r - top.r) * t),
                int(top.g + (bottom.g - top.g) * t),
                int(top.b + (bottom.b - top.b) * t),
            )
            pygame.draw.line(self.screen, color, (0, y), (width, y))
        for x in range(-height, width + 220, 128):
            pygame.draw.line(self.screen, (176, 192, 205), (x, 0), (x + height, height), 1)
        for y in range(0, height, 86):
            pygame.draw.line(self.screen, (203, 214, 224), (0, y), (width, y), 1)
        left_band = pygame.Rect(0, 0, max(180, width // 6), 54)
        right_band = pygame.Rect(width - max(220, width // 5), 0, max(220, width // 5), 68)
        pygame.draw.rect(self.screen, theme.paper, left_band)
        pygame.draw.rect(self.screen, theme.paper_alt, right_band)
        pygame.draw.rect(self.screen, theme.warning, pygame.Rect(right_band.x, right_band.bottom - 8, right_band.width, 8))

    def _draw_card(
        self,
        rect: pygame.Rect,
        *,
        fill: tuple[int, int, int] | tuple[int, int, int, int] = (27, 41, 57),
        border: tuple[int, int, int] | tuple[int, int, int, int] = (93, 117, 141),
        radius: int = 16,
        shadow: int = 5,
    ) -> None:
        theme = self.ui_theme
        fill_rgb = fill[:3]
        border_rgb = border[:3]
        fill_alpha = fill[3] if len(fill) == 4 else 255
        border_alpha = border[3] if len(border) == 4 else 255
        if shadow > 0:
            shadow_rect = rect.move(0, shadow)
            shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surface, theme.shadow, shadow_surface.get_rect(), border_radius=radius)
            self.screen.blit(shadow_surface, shadow_rect.topleft)
        if fill_alpha < 255 or border_alpha < 255:
            card_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(card_surface, (*fill_rgb, fill_alpha), card_surface.get_rect(), border_radius=radius)
            self.screen.blit(card_surface, rect.topleft)
        else:
            pygame.draw.rect(self.screen, fill_rgb, rect, border_radius=radius)
        highlight = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, max(2, int(rect.height * 0.14)))
        overlay = pygame.Surface((highlight.width, highlight.height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 20 if not self._high_contrast_enabled() else 12))
        self.screen.blit(overlay, highlight.topleft)
        if border_alpha < 255:
            border_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(border_surface, (*border_rgb, border_alpha), border_surface.get_rect(), 2, border_radius=radius)
            self.screen.blit(border_surface, rect.topleft)
        else:
            pygame.draw.rect(self.screen, border_rgb, rect, 2, border_radius=radius)

    def _draw_button(self, rect: pygame.Rect, label: str, *, active: bool, compact: bool = False, kind: str = "secondary") -> None:
        theme = self.ui_theme
        tone = {
            "primary": (theme.dark_surface, theme.warning, theme.light_ink),
            "secondary": (theme.paper, theme.border, theme.ink),
            "danger": (theme.paper, theme.danger, theme.ink),
        }.get(kind, (theme.surface, theme.border, theme.ink))
        fill, border, ink = tone
        if active:
            border = theme.warning
        self._draw_card(rect, fill=fill, border=border, radius=theme.radius_small if compact else theme.radius_medium, shadow=2)
        accent_bar = pygame.Rect(rect.x + 8, rect.y + 8, 5, rect.height - 16)
        pygame.draw.rect(self.screen, border, accent_bar, border_radius=3)
        if active:
            glow = pygame.Rect(rect.x - 2, rect.y - 2, rect.width + 4, rect.height + 4)
            pygame.draw.rect(self.screen, theme.warning, glow, 2, border_radius=(theme.radius_small if compact else theme.radius_medium) + 2)
        if label:
            font = self.fonts["small"] if compact else self.fonts["heading"]
            text = font.render(label, True, ink)
            self.screen.blit(text, text.get_rect(center=(rect.centerx + 10, rect.centery)))

    def _draw_panel(self, rect: pygame.Rect, fill: tuple[int, int, int] | None = None) -> None:
        theme = self.ui_theme
        self._draw_card(rect, fill=fill or theme.surface, border=theme.border, radius=theme.radius_medium, shadow=4)

    def _draw_modal(self, rect: pygame.Rect, title: str, *, eyebrow: str = "") -> None:
        theme = self.ui_theme
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(theme.overlay)
        self.screen.blit(overlay, (0, 0))
        self._draw_card(rect, fill=theme.paper, border=theme.border, radius=theme.radius_large, shadow=8)
        header = pygame.Rect(rect.x + 14, rect.y + 14, rect.width - 28, 74)
        self._draw_card(header, fill=theme.paper_alt, border=theme.border, radius=theme.radius_medium, shadow=0)
        stripe = pygame.Rect(header.x, header.y, header.width, 8)
        pygame.draw.rect(self.screen, theme.warning, stripe, border_top_left_radius=theme.radius_medium, border_top_right_radius=theme.radius_medium)
        if eyebrow:
            eyebrow_surface = self.fonts["tiny"].render(eyebrow, True, theme.info)
            self.screen.blit(eyebrow_surface, (header.x + 18, header.y + 16))
        title_surface = self.fonts["title"].render(title, True, theme.ink)
        self.screen.blit(title_surface, (header.x + 18, header.y + 28))
        hint_rect = pygame.Rect(header.right - 64, header.y + 14, 46, 24)
        self._draw_card(hint_rect, fill=theme.surface, border=theme.warning, radius=theme.radius_small, shadow=0)
        hint = self.fonts["tiny"].render("Esc", True, theme.warning)
        self.screen.blit(hint, hint.get_rect(center=hint_rect.center))

    def _draw_dual_text(self, rect: pygame.Rect, primary: str, secondary: str) -> None:
        self._draw_wrapped(self.screen, self.fonts["small"], primary, self.ui_theme.ink, pygame.Rect(rect.x, rect.y, rect.width, 26), self.fonts["small"].get_linesize())
        self._draw_wrapped(self.screen, self.fonts["tiny"], secondary, self.ui_theme.muted, pygame.Rect(rect.x, rect.y + 24, rect.width, rect.height - 24), self.fonts["tiny"].get_linesize())

    def _draw_wrapped(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        color: tuple[int, int, int] | pygame.Color,
        rect: pygame.Rect,
        line_height: int,
        *,
        max_lines: int | None = None,
        ellipsis: bool = False,
    ) -> None:
        y = rect.y
        lines = self._wrap_text(font, text, rect.width)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            if ellipsis and lines:
                lines[-1] = self._ellipsize_text(font, lines[-1], rect.width)
        for line in lines:
            if y + line_height > rect.bottom and y != rect.y:
                break
            rendered = font.render(line, True, color)
            surface.blit(rendered, (rect.x, y))
            y += line_height

    def _ellipsize_text(self, font: pygame.font.Font, text: str, width: int) -> str:
        if font.size(text)[0] <= width:
            return text
        ellipsis = "..."
        current = text
        while current and font.size(current + ellipsis)[0] > width:
            current = current[:-1]
        return current + ellipsis

    def _wrap_text(self, font: pygame.font.Font, text: str, width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in text.split("\n"):
            units = paragraph.split(" ") if " " in paragraph else list(paragraph)
            current = ""
            for index, unit in enumerate(units):
                part = unit if " " not in paragraph else (unit if not current else f" {unit}")
                trial = current + part
                if font.size(trial)[0] <= width or not current:
                    current = trial
                else:
                    lines.append(current)
                    current = unit if " " not in paragraph else unit
            if current:
                lines.append(current)
            elif not lines:
                lines.append("")
        return lines
