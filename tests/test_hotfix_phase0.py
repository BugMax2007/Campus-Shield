from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from campus_safe_game.game import AppConfig, CampusSafeGame


class HotfixPhase0Test(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(__file__).resolve().parents[1]

    def tearDown(self) -> None:
        pygame.display.quit()
        pygame.quit()

    def test_all_spawns_are_navigable(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="random", resolution=(1280, 720)))
        for scene in game.content.scenes.values():
            for spawn in scene.spawns:
                self.assertTrue(
                    game._spawn_is_valid(spawn),
                    f"spawn not navigable: scene={scene.id} spawn={spawn.id}",
                )

    def test_random_spawn_is_indoor(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="random", resolution=(1280, 720)))
        for _ in range(10):
            game.start_session()
            assert game.session is not None
            self.assertNotEqual(game.session.scene_id, "outdoor_main")

    def test_raider_dispatch_reaches_player_scene(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        assert game.session is not None
        game._skip_opening()
        game.session.scene_id = "library_f1"
        game.session.player_x = 1960
        game.session.player_y = 1260
        game.session.global_chase_active = True
        game.session.global_chase_timer = 12.0
        target = game.actor_states["raider_sc_patrol"]
        self.assertNotEqual(target.scene_id, game.session.scene_id)
        for _ in range(120):
            game._update_actor_ai(0.2)
            if target.scene_id == game.session.scene_id:
                break
        self.assertEqual(target.scene_id, game.session.scene_id)

    def test_raider_cannot_cross_solid_wall(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_sc_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        raider = game.actor_states["raider_sc_patrol"]
        raider.scene_id = "student_center_f1"
        raider.x = 980
        raider.y = 500
        for _ in range(50):
            game._actor_move_towards(raider, (1300, 500), 0.2, 140)
        # student_center_f1 central wall starts at x=1080 and is solid
        self.assertLess(raider.x, 1080)

    def test_scene_nav_path_routes_around_wall(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_sc_f1_entrance", resolution=(1280, 720)))
        path = game._scene_nav_path("student_center_f1", (980, 500), (1300, 500))
        self.assertTrue(path, "expected non-empty nav path around central wall")
        self.assertGreater(len(path), 1)
        self.assertAlmostEqual(path[-1][0], 1300, delta=1.0)
        self.assertAlmostEqual(path[-1][1], 500, delta=1.0)

    def test_actor_seek_can_progress_around_wall(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_sc_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        raider = game.actor_states["raider_sc_patrol"]
        raider.scene_id = "student_center_f1"
        raider.x = 980
        raider.y = 500
        for _ in range(80):
            game._actor_seek(raider, (1300, 500), 0.2, 140)
        self.assertGreater(raider.x, 1080)

    def test_security_robot_posts_warning_near_raider(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_sc_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        assert game.session is not None
        game.session.scene_id = "student_center_f1"
        game.session.player_x = 620
        game.session.player_y = 1320
        security = game.actor_states["security_robot"]
        raider = game.actor_states["raider_sc_patrol"]
        security.scene_id = "student_center_f1"
        security.x = 520
        security.y = 1320
        raider.scene_id = "student_center_f1"
        raider.x = 760
        raider.y = 1320
        game._update_robot(game.actor_defs["security_robot"], security, 0.1)
        self.assertTrue(any(title == game.localizer.text("robot.security.notice") for _, title, _ in game.session.message_history))

    def test_pause_buttons_are_clickable(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        assert game.session is not None
        game.session.paused = True
        game._render()
        self.assertGreaterEqual(len(game.pause_buttons), 3)
        menu_rect, action = game.pause_buttons[1]
        self.assertEqual(action, "menu")
        game._handle_play_click(menu_rect.center)
        self.assertEqual(game.view, "menu")

    def test_scene_path_respects_blocked_links(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_outdoor_center", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        assert game.session is not None
        game.session.phase = "Alert"
        game.session.blocked_links = {"link_outdoor_to_student_center"}
        blocked_path = game._scene_path("outdoor_main", "student_center_f2", allow_blocked=False)
        fallback_path = game._scene_path("outdoor_main", "student_center_f2", allow_blocked=True)
        self.assertEqual(blocked_path, [])
        self.assertGreaterEqual(len(fallback_path), 2)

    def test_gate_exit_reason_when_not_outdoor(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        assert game.session is not None
        game.session.scene_id = "library_f1"
        self.assertEqual(game._gate_exit_block_reason(), "ui.exit_not_in_gate_scene")

    def test_route_labels_returns_state(self) -> None:
        game = CampusSafeGame(self.base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        assert game.session is not None
        labels, state = game._route_to_scene_labels("outdoor_main")
        self.assertGreaterEqual(len(labels), 2)
        self.assertIn(state, {"ui.map_route_open", "ui.map_route_blocked"})


if __name__ == "__main__":
    unittest.main()
