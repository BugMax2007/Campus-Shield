from __future__ import annotations

import unittest
from pathlib import Path

from campus_safe_game.advisor import CampusAdvisor


class AdvisorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(__file__).resolve().parents[1]
        self.advisor = CampusAdvisor(self.base)

    def test_collect_clues_strategy_uses_fallback(self) -> None:
        decision = self.advisor.evaluate(
            "zh-CN",
            {
                "scene_id": "student_center_f1",
                "phase": "Alert",
                "safe": True,
                "near_map_board": False,
                "clues_found": 1,
                "required_clues": 3,
                "bottles": 2,
                "route_gate": "学生中心 1 层 -> 室外层",
                "route_secret": "学生中心 1 层 -> 图书馆 2 层",
                "gate_reason": "ui.exit_blocked_guardline",
                "gate_reason_text": "北门守卫正面视线覆盖，当前无法通过。",
                "default_gate_reason": "移动到北门场景后再尝试。",
                "default_route_unknown": "暂无路线",
                "at_gate_scene": False,
                "alert_elapsed": 60.0,
                "survive_seconds": 420,
                "map_reads": 1,
                "state_text": "alert state with incomplete clues",
            },
        )
        self.assertEqual(decision.strategy, "collect_clues")
        self.assertIn("线索", decision.headline + decision.summary + decision.route_value)

    def test_gate_window_strategy(self) -> None:
        decision = self.advisor.evaluate(
            "en-US",
            {
                "scene_id": "outdoor_main",
                "phase": "Alert",
                "safe": False,
                "near_map_board": False,
                "clues_found": 3,
                "required_clues": 3,
                "bottles": 1,
                "route_gate": "Outdoor Layer",
                "route_secret": "Library Floor 2",
                "gate_reason": None,
                "gate_reason_text": "",
                "default_gate_reason": "Move to gate first",
                "default_route_unknown": "Unknown",
                "at_gate_scene": True,
                "alert_elapsed": 100.0,
                "survive_seconds": 420,
                "map_reads": 2,
                "state_text": "alert state with open gate",
            },
        )
        self.assertEqual(decision.strategy, "take_gate_now")
        self.assertIn("gate", decision.summary.lower() + decision.detail.lower())


if __name__ == "__main__":
    unittest.main()
