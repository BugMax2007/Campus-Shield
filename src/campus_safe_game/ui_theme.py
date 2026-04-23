from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pygame


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


@dataclass(frozen=True)
class UIFonts:
    display: pygame.font.Font
    title: pygame.font.Font
    heading: pygame.font.Font
    body: pygame.font.Font
    small: pygame.font.Font
    tiny: pygame.font.Font
    mono: pygame.font.Font


@dataclass(frozen=True)
class UITheme:
    fonts: UIFonts
    ink: tuple[int, int, int]
    muted: tuple[int, int, int]
    surface: tuple[int, int, int]
    surface_alt: tuple[int, int, int]
    surface_soft: tuple[int, int, int]
    border: tuple[int, int, int]
    shadow: tuple[int, int, int, int]
    accent: tuple[int, int, int]
    accent_soft: tuple[int, int, int]
    info: tuple[int, int, int]
    success: tuple[int, int, int]
    danger: tuple[int, int, int]
    warning: tuple[int, int, int]
    dark_surface: tuple[int, int, int]
    dark_border: tuple[int, int, int]
    light_ink: tuple[int, int, int]
    overlay: tuple[int, int, int, int]
    canvas_top: tuple[int, int, int]
    canvas_bottom: tuple[int, int, int]
    paper: tuple[int, int, int]
    paper_alt: tuple[int, int, int]
    safe_margin: int
    gap: int
    small_gap: int
    radius_large: int
    radius_medium: int
    radius_small: int


def _pick_font_path(base_path: Path) -> str | None:
    asset_candidates = [
        base_path / "assets" / "ui" / "fonts" / "NotoSansSC-Medium.otf",
        base_path / "assets" / "ui" / "fonts" / "NotoSansSC-Regular.otf",
    ]
    for path in asset_candidates:
        if path.exists():
            return str(path)
    system_candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKSC-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    windir = os.environ.get("WINDIR")
    if windir:
        windows_fonts = Path(windir) / "Fonts"
        system_candidates = [
            str(windows_fonts / "msyh.ttc"),
            str(windows_fonts / "msyhbd.ttc"),
            str(windows_fonts / "msyh.ttf"),
            str(windows_fonts / "simhei.ttf"),
            str(windows_fonts / "simsun.ttc"),
            str(windows_fonts / "simkai.ttf"),
            str(windows_fonts / "arialuni.ttf"),
            str(windows_fonts / "segoeui.ttf"),
            *system_candidates,
        ]
    for path in system_candidates:
        if Path(path).exists():
            return str(path)
    for name in (
        "Hiragino Sans GB",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Microsoft YaHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ):
        # pygame's Windows sysfont lookup can fail on some hosts while walking the
        # registry. Treat that as a soft failure and fall back to the default font.
        try:
            font_path = pygame.font.match_font(name)
        except Exception:
            continue
        if isinstance(font_path, (str, os.PathLike)) and font_path:
            return font_path
    return None


def build_theme(base_path: Path, screen_size: tuple[int, int], high_contrast: bool = False) -> UITheme:
    width, height = screen_size
    safe_margin = _clamp(int(min(width, height) * 0.045), 28, 56)
    gap = _clamp(int(min(width, height) * 0.018), 14, 26)
    font_path = _pick_font_path(base_path)
    fonts = UIFonts(
        display=pygame.font.Font(font_path, _clamp(int(height * 0.072), 42, 72)),
        title=pygame.font.Font(font_path, _clamp(int(height * 0.050), 30, 48)),
        heading=pygame.font.Font(font_path, _clamp(int(height * 0.032), 20, 30)),
        body=pygame.font.Font(font_path, _clamp(int(height * 0.025), 16, 24)),
        small=pygame.font.Font(font_path, _clamp(int(height * 0.020), 14, 19)),
        tiny=pygame.font.Font(font_path, _clamp(int(height * 0.016), 12, 15)),
        mono=pygame.font.Font(font_path, _clamp(int(height * 0.018), 13, 17)),
    )

    if high_contrast:
        return UITheme(
            fonts=fonts,
            ink=(245, 248, 250),
            muted=(205, 216, 226),
            surface=(6, 10, 16),
            surface_alt=(12, 18, 27),
            surface_soft=(19, 28, 40),
            border=(227, 233, 239),
            shadow=(0, 0, 0, 170),
            accent=(252, 211, 77),
            accent_soft=(92, 66, 20),
            info=(96, 165, 250),
            success=(74, 222, 128),
            danger=(248, 113, 113),
            warning=(251, 191, 36),
            dark_surface=(6, 10, 16),
            dark_border=(214, 223, 232),
            light_ink=(248, 250, 252),
            overlay=(2, 6, 10, 212),
            canvas_top=(8, 14, 21),
            canvas_bottom=(11, 20, 31),
            paper=(14, 20, 28),
            paper_alt=(20, 30, 42),
            safe_margin=safe_margin,
            gap=gap,
            small_gap=max(10, int(gap * 0.7)),
            radius_large=20,
            radius_medium=14,
            radius_small=9,
        )

    return UITheme(
        fonts=fonts,
        ink=(25, 39, 53),
        muted=(93, 108, 120),
        surface=(245, 243, 237),
        surface_alt=(231, 237, 241),
        surface_soft=(214, 225, 232),
        border=(72, 94, 111),
        shadow=(10, 18, 28, 46),
        accent=(239, 190, 63),
        accent_soft=(169, 129, 47),
        info=(74, 135, 176),
        success=(74, 132, 101),
        danger=(167, 82, 80),
        warning=(226, 162, 46),
        dark_surface=(24, 39, 54),
        dark_border=(117, 141, 160),
        light_ink=(247, 250, 252),
        overlay=(10, 18, 28, 120),
        canvas_top=(229, 235, 241),
        canvas_bottom=(188, 204, 218),
        paper=(250, 248, 242),
        paper_alt=(237, 241, 243),
        safe_margin=safe_margin,
        gap=gap,
        small_gap=max(10, int(gap * 0.7)),
        radius_large=20,
        radius_medium=14,
        radius_small=9,
    )
