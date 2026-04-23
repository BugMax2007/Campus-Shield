from __future__ import annotations

import unittest

from campus_safe_game.layout import build_layout, build_screen_layout


class LayoutTest(unittest.TestCase):
    def test_anchor_layout_stays_inside_safe_margin(self) -> None:
        for size in ((1280, 720), (1600, 900), (1920, 1080)):
            layout = build_layout(size)
            screen_layout = build_screen_layout(size)
            width, height = size
            margin = screen_layout.safe_margin
            for rect in layout.values():
                self.assertGreaterEqual(rect.left, margin - 2)
                self.assertGreaterEqual(rect.top, margin - 2)
                self.assertLessEqual(rect.right, width - margin + 2)
                self.assertLessEqual(rect.bottom, height - margin + 2)

    def test_main_panels_do_not_overlap(self) -> None:
        layout = build_layout((1600, 900))
        self.assertFalse(layout["location_chip"].colliderect(layout["route_chip"]))
        self.assertFalse(layout["location_chip"].colliderect(layout["status_bar"]))
        self.assertFalse(layout["route_chip"].colliderect(layout["status_bar"]))
        self.assertFalse(layout["subtitles"].colliderect(layout["action_bar"]))


if __name__ == "__main__":
    unittest.main()
