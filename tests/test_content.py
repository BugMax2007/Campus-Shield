from __future__ import annotations

from pathlib import Path
import unittest

from campus_safe_game.loader import load_content


class ContentContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base_path = Path(__file__).resolve().parents[1]

    def test_scene_graph_loads(self) -> None:
        content = load_content(self.base_path)
        self.assertGreaterEqual(len(content.scenes), 5)
        self.assertIn("outdoor_main", content.scenes)
        self.assertGreaterEqual(len(content.actors), 5)

    def test_every_scene_has_map_board(self) -> None:
        content = load_content(self.base_path)
        for scene in content.scenes.values():
            self.assertGreaterEqual(len(scene.map_boards), 1)

    def test_scenario_clues_exist(self) -> None:
        content = load_content(self.base_path)
        interaction_ids = {item.id for item in content.interactions}
        for clue_id in content.scenario.clue_chain:
            self.assertIn(clue_id, interaction_ids)


if __name__ == "__main__":
    unittest.main()
