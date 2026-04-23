from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from campus_safe_game.ui_theme import _pick_font_path


class UIThemeTest(unittest.TestCase):
    def test_pick_font_path_survives_sysfont_failure(self) -> None:
        base = Path(__file__).resolve().parents[1]
        with mock.patch("campus_safe_game.ui_theme.Path.exists", return_value=False):
            with mock.patch("campus_safe_game.ui_theme.pygame.font.match_font", side_effect=TypeError("broken sysfont")):
                font_path = _pick_font_path(base)
        self.assertIsNone(font_path)


if __name__ == "__main__":
    unittest.main()
