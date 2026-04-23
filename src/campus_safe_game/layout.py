from __future__ import annotations

from dataclasses import dataclass

import pygame


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ScreenLayout:
    safe_margin: int
    outer: pygame.Rect
    menu_hero: pygame.Rect
    menu_visual: pygame.Rect
    menu_actions: pygame.Rect
    menu_help: pygame.Rect
    alert_bar: pygame.Rect
    location_chip: pygame.Rect
    route_chip: pygame.Rect
    status_bar: pygame.Rect
    subtitles: pygame.Rect
    action_bar: pygame.Rect
    modal: pygame.Rect
    modal_header: pygame.Rect
    modal_body: pygame.Rect


def build_layout(screen_size: tuple[int, int]) -> dict[str, pygame.Rect]:
    layout = build_screen_layout(screen_size)
    return {
        "menu_hero": layout.menu_hero,
        "menu_visual": layout.menu_visual,
        "menu_actions": layout.menu_actions,
        "menu_help": layout.menu_help,
        "alert_bar": layout.alert_bar,
        "location_chip": layout.location_chip,
        "route_chip": layout.route_chip,
        "status_bar": layout.status_bar,
        "subtitles": layout.subtitles,
        "action_bar": layout.action_bar,
        "modal": layout.modal,
        "modal_header": layout.modal_header,
        "modal_body": layout.modal_body,
    }


def build_screen_layout(screen_size: tuple[int, int]) -> ScreenLayout:
    width, height = screen_size
    safe_margin = _clamp(int(min(width, height) * 0.045), 28, 56)
    gap = _clamp(int(min(width, height) * 0.018), 14, 26)
    small_gap = _clamp(int(gap * 0.7), 10, 18)

    outer = pygame.Rect(safe_margin, safe_margin, width - safe_margin * 2, height - safe_margin * 2)

    hero_h = _clamp(int(height * 0.19), 138, 210)
    hero = pygame.Rect(outer.x, outer.y, outer.width, hero_h)

    bottom_h = outer.height - hero.height - gap
    visual_w = int(outer.width * 0.52)
    actions_w = int(outer.width * 0.24)
    menu_visual = pygame.Rect(outer.x, hero.bottom + gap, visual_w, bottom_h)
    menu_actions = pygame.Rect(menu_visual.right + gap, menu_visual.y, actions_w, bottom_h)
    menu_help = pygame.Rect(menu_actions.right + gap, menu_visual.y, outer.right - (menu_actions.right + gap), bottom_h)

    alert_h = _clamp(int(height * 0.060), 42, 64)
    alert_bar = pygame.Rect(outer.x, outer.y, outer.width, alert_h)

    chip_h = _clamp(int(height * 0.078), 52, 70)
    location_w = _clamp(int(width * 0.21), 230, 360)
    route_w = _clamp(int(width * 0.31), 280, 500)
    status_w = _clamp(int(width * 0.21), 240, 360)

    location_chip = pygame.Rect(outer.x, alert_bar.bottom + small_gap, location_w, chip_h)
    route_chip = pygame.Rect(
        location_chip.right + gap,
        alert_bar.bottom + small_gap,
        outer.width - location_w - status_w - gap * 2,
        chip_h,
    )
    status_bar = pygame.Rect(outer.right - status_w, alert_bar.bottom + small_gap, status_w, chip_h)

    subtitles_h = _clamp(int(height * 0.15), 92, 138)
    subtitles_w = _clamp(int(width * 0.28), 280, 420)
    subtitles = pygame.Rect(outer.x, outer.bottom - subtitles_h, subtitles_w, subtitles_h)

    action_h = _clamp(int(height * 0.066), 48, 68)
    action_w = _clamp(int(width * 0.34), 360, 560)
    action_bar = pygame.Rect(
        outer.right - action_w,
        outer.bottom - action_h,
        action_w,
        action_h,
    )

    modal = pygame.Rect(int(width * 0.075), int(height * 0.07), int(width * 0.85), int(height * 0.86))
    modal_header = pygame.Rect(modal.x, modal.y, modal.width, _clamp(int(height * 0.11), 72, 100))
    modal_body = pygame.Rect(modal.x + 22, modal_header.bottom + 10, modal.width - 44, modal.bottom - modal_header.bottom - 32)

    return ScreenLayout(
        safe_margin=safe_margin,
        outer=outer,
        menu_hero=hero,
        menu_visual=menu_visual,
        menu_actions=menu_actions,
        menu_help=menu_help,
        alert_bar=alert_bar,
        location_chip=location_chip,
        route_chip=route_chip,
        status_bar=status_bar,
        subtitles=subtitles,
        action_bar=action_bar,
        modal=modal,
        modal_header=modal_header,
        modal_body=modal_body,
    )


def split_columns(rect: pygame.Rect, left_ratio: float, gap: int) -> tuple[pygame.Rect, pygame.Rect]:
    left_w = int((rect.width - gap) * left_ratio)
    left = pygame.Rect(rect.x, rect.y, left_w, rect.height)
    right = pygame.Rect(left.right + gap, rect.y, rect.width - left.width - gap, rect.height)
    return left, right


def stack_rows(rect: pygame.Rect, heights: list[int], gap: int) -> list[pygame.Rect]:
    rows: list[pygame.Rect] = []
    y = rect.y
    for index, height in enumerate(heights):
        rows.append(pygame.Rect(rect.x, y, rect.width, height))
        y += height
        if index != len(heights) - 1:
            y += gap
    return rows
