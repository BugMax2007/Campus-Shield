from __future__ import annotations

import json
from pathlib import Path
import unittest


class GodotLevelDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(__file__).resolve().parents[1]
        level_path = self.base / "godot" / "data" / "levels" / "chapter_01.json"
        self.level = json.loads(level_path.read_text(encoding="utf-8"))
        self.layers = {layer["name"]: layer for layer in self.level["layers"]}

    def test_required_tiled_layers_exist(self) -> None:
        required = {
            "ground",
            "walls",
            "cover",
            "rooms",
            "interactables",
            "spawns",
            "patrol_paths",
            "exits",
            "signage",
            "actors",
        }
        self.assertTrue(required.issubset(self.layers.keys()))

    def test_rooms_have_safety_contract(self) -> None:
        rooms = self.layers["rooms"]["objects"]
        self.assertGreaterEqual(len(rooms), 6)
        for room in rooms:
            props = self._props(room)
            for key in ("room_id", "room_name", "risk_level", "safe_tags"):
                self.assertIn(key, props)
            self.assertIn(props["risk_level"], {"safe", "risk"})

    def test_interactables_have_education_contract(self) -> None:
        interactables = self.layers["interactables"]["objects"]
        interaction_types = {self._props(obj)["interaction_type"] for obj in interactables}
        self.assertIn("map_board", interaction_types)
        self.assertIn("official_notice", interaction_types)
        self.assertIn("door_lock", interaction_types)
        self.assertIn("route_sign", interaction_types)
        self.assertGreaterEqual(sum(1 for obj in interactables if self._props(obj)["interaction_type"] == "clue"), 3)
        for obj in interactables:
            props = self._props(obj)
            for key in ("interaction_id", "interaction_type", "label", "education_key", "effect_type", "required_phase", "route_value", "feedback_key"):
                self.assertIn(key, props)

    def test_chapter_one_has_concrete_stealth_spaces(self) -> None:
        room_names = " ".join(self._props(obj)["room_name"] for obj in self.layers["rooms"]["objects"])
        for expected in ("图书馆入口", "书架区", "学生中心大厅", "教室 A", "教室 B", "办公室", "储藏间", "服务通道"):
            self.assertIn(expected, room_names)
        cover_names = {obj["name"] for obj in self.layers["cover"]["objects"]}
        self.assertGreaterEqual(sum(1 for name in cover_names if "bookshelf" in name), 4)
        self.assertGreaterEqual(sum(1 for name in cover_names if "table" in name), 5)

    def test_interaction_effects_cover_gameplay_loop(self) -> None:
        effects = {self._props(obj)["effect_type"] for obj in self.layers["interactables"]["objects"]}
        for expected in ("unlock_map", "trigger_alert", "validate_safe_room", "service_clue", "commit_main_exit", "commit_service_route"):
            self.assertIn(expected, effects)

    def test_raider_roles_cover_gate_library_student_and_service(self) -> None:
        actors = [self._props(obj) for obj in self.layers["actors"]["objects"]]
        raiders = [actor for actor in actors if actor["actor_kind"] == "raider"]
        self.assertGreaterEqual(len(raiders), 4)
        linked_paths = {actor["patrol_id"] for actor in raiders}
        self.assertIn("gate_guard_path", linked_paths)
        self.assertIn("library_search_path", linked_paths)
        self.assertIn("student_center_path", linked_paths)
        self.assertIn("service_hall_path", linked_paths)

    def test_patrol_paths_and_actors_are_linked(self) -> None:
        paths = {self._props(obj)["patrol_id"] for obj in self.layers["patrol_paths"]["objects"]}
        self.assertGreaterEqual(len(paths), 4)
        for path_obj in self.layers["patrol_paths"]["objects"]:
            props = self._props(path_obj)
            self.assertIn("raider_role", props)
            self.assertIn("path_points", props)
            self.assertGreaterEqual(len(path_obj.get("polyline", [])), 4)
        for actor in self.layers["actors"]["objects"]:
            props = self._props(actor)
            if props["actor_kind"] == "raider":
                self.assertIn(props["patrol_id"], paths)

    def test_exit_routes_are_complete(self) -> None:
        exits = {self._props(obj)["exit_type"]: self._props(obj) for obj in self.layers["exits"]["objects"]}
        self.assertIn("main", exits)
        self.assertIn("secret", exits)
        self.assertEqual(int(exits["secret"]["required_clues"]), 3)

    def test_level_has_readable_detail_props(self) -> None:
        cover_names = {obj["name"] for obj in self.layers["cover"]["objects"]}
        self.assertTrue(any("shelf" in name for name in cover_names), "library needs visible bookshelf cover")
        self.assertTrue(any("table" in name for name in cover_names), "library/student rooms need visible tables")
        signage_labels = " ".join(self._props(obj).get("label", "") for obj in self.layers["signage"]["objects"])
        self.assertIn("出口", signage_labels)
        self.assertIn("服务通道", signage_labels)

    def _props(self, obj: dict) -> dict:
        return {prop["name"]: prop["value"] for prop in obj.get("properties", [])}


if __name__ == "__main__":
    unittest.main()
