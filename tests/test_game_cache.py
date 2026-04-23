from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from campus_safe_game.game import AppConfig, CampusSafeGame


class GameFlowTest(unittest.TestCase):
    def test_opening_sequence_progresses(self) -> None:
        base = Path(__file__).resolve().parents[1]
        game = CampusSafeGame(base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        self.assertTrue(game.session.opening_active)
        game._skip_opening()
        self.assertFalse(game.session.opening_active)
        pygame.display.quit()
        pygame.quit()

    def test_throw_bottle_consumes_inventory(self) -> None:
        base = Path(__file__).resolve().parents[1]
        game = CampusSafeGame(base, AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(1280, 720)))
        game.start_session()
        game._skip_opening()
        before = game.session.bottles
        game._throw_bottle()
        self.assertEqual(game.session.bottles, before - 1)
        self.assertGreaterEqual(len(game.noises), 1)
        pygame.display.quit()
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
