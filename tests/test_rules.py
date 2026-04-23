from __future__ import annotations

import unittest

from campus_safe_game.models import AreaTrigger
from campus_safe_game.rules import (
    ScoreCard,
    build_debrief_feedback_keys,
    build_objective_checklist,
    qualifies_safe_area,
)


class RulesTest(unittest.TestCase):
    def test_scorecard_caps_values(self) -> None:
        score = ScoreCard()
        score.add("space_choice", 99)
        score.add("official_info", 99)
        self.assertEqual(score.values["space_choice"], 30)
        self.assertEqual(score.values["official_info"], 25)

    def test_safe_area_requires_all_tags(self) -> None:
        trigger = AreaTrigger(
            id="safe",
            label_key="trigger.library_archive_safe",
            tags=("lockable", "out_of_sight", "not_public_corridor", "not_glass_exposed"),
            x=0,
            y=0,
            width=100,
            height=100,
        )
        self.assertTrue(
            qualifies_safe_area(
                trigger,
                ("lockable", "out_of_sight", "not_public_corridor", "not_glass_exposed"),
            )
        )

    def test_objective_checklist_for_shelter(self) -> None:
        checklist = build_objective_checklist(
            "Shelter",
            unread_alert=False,
            map_reads=1,
            floor_changes=2,
            clues=2,
            bottle_throws=1,
            safe_seconds=10,
            captured=False,
            exit_attempts=0,
        )
        self.assertIn(("check.shelter_find_safe_room", True), checklist)
        self.assertIn(("check.shelter_avoid_capture", True), checklist)

    def test_debrief_feedback_contains_expected_keys(self) -> None:
        keys = build_debrief_feedback_keys(
            ending="exit_gate",
            captured=False,
            clues=3,
            bottle_throws=2,
            alerts_ignored=0,
            safe_seconds=30,
        )
        self.assertIn("feedback.ending.exit_gate", keys)
        self.assertIn("feedback.capture.good", keys)
        self.assertIn("feedback.clue.good", keys)


if __name__ == "__main__":
    unittest.main()
