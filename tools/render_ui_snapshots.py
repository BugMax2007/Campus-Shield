from __future__ import annotations

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from campus_safe_game.game import AppConfig, CampusSafeGame


RESOLUTIONS = ((1280, 720), (1600, 900), (1920, 1080))


def main() -> None:
    base = ROOT
    output_dir = base / "artifacts" / "snapshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    for width, height in RESOLUTIONS:
        game = CampusSafeGame(
            base,
            AppConfig(mode="practice", language="zh-CN", spawn_id="spawn_library_f1_entrance", resolution=(width, height)),
        )
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"menu_{width}x{height}.png"))

        game.start_session()
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"opening_{width}x{height}.png"))

        game._skip_opening()
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"gameplay_{width}x{height}.png"))

        game.session.elapsed = 130
        game._advance_alerts()
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"alert_{width}x{height}.png"))

        game.session.player_x = 1338
        game.session.player_y = 778
        game.session.map_open = True
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"map_{width}x{height}.png"))

        game.session.map_open = False
        game.session.phone_open = True
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"phone_{width}x{height}.png"))

        game.session.phone_open = False
        game.session.log_open = True
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"log_{width}x{height}.png"))

        game.session.log_open = False
        game.session.paused = True
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"pause_{width}x{height}.png"))

        game.session.paused = False
        game.session.safe_seconds = 36
        game.session.clues_found.update({"clue_library_terminal", "clue_robot_dock", "clue_sc_notice_board"})
        game._finish_session("success", "success.secret_tunnel", "secret_tunnel")
        game._render()
        pygame.image.save(game.screen, str(output_dir / f"debrief_{width}x{height}.png"))

        pygame.display.quit()
        pygame.quit()

    print(f"snapshot export complete: {output_dir}")


if __name__ == "__main__":
    main()
