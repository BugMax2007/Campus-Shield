from __future__ import annotations

import argparse
from pathlib import Path

from .game import AppConfig, CampusSafeGame


def parse_args() -> AppConfig:
    parser = argparse.ArgumentParser(description="Campus Shield")
    parser.add_argument("--mode", choices=["story", "practice"], default="story")
    parser.add_argument("--lang", choices=["zh-CN", "en-US"], default="zh-CN")
    parser.add_argument("--spawn", default="random")
    parser.add_argument("--resolution", default="1600x900")
    parser.add_argument("--fullscreen", action="store_true")
    args = parser.parse_args()
    width_str, height_str = args.resolution.lower().split("x", 1)
    return AppConfig(
        mode=args.mode,
        language=args.lang,
        spawn_id=args.spawn,
        resolution=(int(width_str), int(height_str)),
        fullscreen=args.fullscreen,
    )


def main() -> None:
    config = parse_args()
    base_path = Path(__file__).resolve().parents[2]
    game = CampusSafeGame(base_path, config)
    game.run()


if __name__ == "__main__":
    main()
