from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from campus_safe_game.models import SaveState
from campus_safe_game.persistence import SaveManager


class SaveManagerTest(unittest.TestCase):
    def test_save_roundtrip_preserves_accessibility_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            manager = SaveManager(path)
            state = SaveState(
                language="en-US",
                completed_runs=3,
                best_score=88,
                unlocked_terms=["official_sources", "secure_room"],
                accessibility_settings={"subtitles": False, "high_contrast": True},
            )
            manager.save(state)
            loaded = manager.load()
            self.assertEqual(loaded.language, "en-US")
            self.assertEqual(loaded.completed_runs, 3)
            self.assertTrue(loaded.accessibility_settings["high_contrast"])
            self.assertFalse(loaded.accessibility_settings["subtitles"])


if __name__ == "__main__":
    unittest.main()

