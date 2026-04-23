from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdvisoryDecision:
    strategy: str
    tone: str
    headline: str
    summary: str
    detail: str
    route_label: str
    route_value: str
    coach_title: str
    coach_body: str
    backend_label: str


class _HeuristicAdvisorBackend:
    name = "heuristic"

    def choose_strategy(self, payload: dict[str, Any]) -> str:
        phase = payload["phase"]
        at_gate_scene = payload["at_gate_scene"]
        gate_reason = payload["gate_reason"]
        clues_found = payload["clues_found"]
        required_clues = payload["required_clues"]
        safe = payload["safe"]
        near_map_board = payload["near_map_board"]
        alert_elapsed = payload["alert_elapsed"]
        survive_seconds = payload["survive_seconds"]

        if phase == "Explore":
            if near_map_board and payload["map_reads"] < 1:
                return "map_and_plan"
            if clues_found < required_clues:
                return "collect_clues"
            return "steady"

        if at_gate_scene and not gate_reason:
            return "take_gate_now"
        if at_gate_scene and gate_reason:
            return "distract_guard"
        if clues_found >= required_clues and payload["scene_id"] == "library_f2":
            return "take_secret_now"
        if safe and alert_elapsed >= survive_seconds * 0.7:
            return "hold_for_police"
        if not safe:
            return "relocate_safe"
        if clues_found < required_clues:
            return "collect_clues"
        return "relocate_to_secret"


class _OptionalHFAdvisorBackend:
    def __init__(self) -> None:
        self._classifier = None
        self._disabled = False
        self.model_id = os.getenv("CAMPUS_SAFE_HF_ROUTE_MODEL", "typeform/distilbert-base-uncased-mnli")

    @property
    def name(self) -> str:
        return "hf" if self.available else "heuristic"

    @property
    def available(self) -> bool:
        return self._ensure_pipeline()

    def _ensure_pipeline(self) -> bool:
        if self._disabled:
            return False
        if self._classifier is not None:
            return True
        if os.getenv("CAMPUS_SAFE_ENABLE_HF", "0") not in {"1", "true", "TRUE", "yes", "YES"}:
            self._disabled = True
            return False
        try:
            from transformers import pipeline

            self._classifier = pipeline("zero-shot-classification", model=self.model_id, device=-1)
            return True
        except Exception:
            self._disabled = True
            self._classifier = None
            return False

    def choose_strategy(self, payload: dict[str, Any]) -> str | None:
        if not self._ensure_pipeline():
            return None
        candidates = {
            "map_and_plan": "Use the nearest map board and form a route before moving deeper.",
            "collect_clues": "Keep collecting route clues from low-risk rooms and official information points.",
            "relocate_safe": "Leave the exposed space and move to a more shielded interior room.",
            "hold_for_police": "Stay in the qualified safe room and wait for police arrival.",
            "take_gate_now": "The main gate window is open. Move now with low exposure.",
            "distract_guard": "Create a distraction before trying the guarded main gate.",
            "relocate_to_secret": "Move toward the secret tunnel route instead of forcing the main gate.",
            "take_secret_now": "The secret tunnel is unlocked. Use it now.",
            "steady": "Maintain a low-risk route and keep confirming official information.",
        }
        state_text = payload["state_text"]
        result = self._classifier(state_text, candidate_labels=list(candidates.values()), multi_label=False)
        top_label = result["labels"][0]
        for key, text in candidates.items():
            if text == top_label:
                return key
        return None


_TEMPLATES = {
    "zh-CN": {
        "backend.hf": "HF 路线模型",
        "backend.heuristic": "本地策略模型",
        "map_and_plan": {
            "tone": "info",
            "headline": "先确认楼层导览，不要盲走",
            "summary": "你还在导览阶段，优先在地图板处确认位置与楼梯连通。",
            "detail": "当前更合适的动作是先看地图板，再决定去主出口、密道或可坚持的安全房间。",
            "route_label": "当前建议",
            "route_value": "就近查看地图板并建立路线心智图",
            "coach_title": "导览建议",
            "coach_body": "先把当前位置、楼梯和下一层路线弄清楚，再移动。",
        },
        "collect_clues": {
            "tone": "warning",
            "headline": "线索还不够，继续低风险收集",
            "summary": "密道尚未完全解锁，先在低暴露房间补齐线索并同步官方信息。",
            "detail": "密道路线：{route_secret}",
            "route_label": "密道进度",
            "route_value": "{clues_found}/{required_clues} 条线索，优先沿低风险路径推进",
            "coach_title": "搜索建议",
            "coach_body": "去低暴露教室、公告板和终端补线索，不要为了速度穿开阔区。",
        },
        "relocate_safe": {
            "tone": "danger",
            "headline": "你处在高暴露位置，先换到内侧空间",
            "summary": "当前位置不是合格避险点，优先离开玻璃区、开放走廊或出口瓶颈。",
            "detail": "先移动到更内侧、遮挡更强、可锁闭的房间，再决定后续路线。",
            "route_label": "当前建议",
            "route_value": "先保命，再撤离",
            "coach_title": "避险建议",
            "coach_body": "先离开当前暴露区，转入内侧房间或书架/隔断后方。",
        },
        "hold_for_police": {
            "tone": "success",
            "headline": "当前安全条件较好，可坚持等待警方",
            "summary": "你已在合格空间内，剩余时间允许你坚持到警方到场。",
            "detail": "警方倒计时：{remaining}s。除非官方更新要求转移，否则保持低暴露。",
            "route_label": "当前建议",
            "route_value": "留在当前安全空间并持续关注官方更新",
            "coach_title": "坚持建议",
            "coach_body": "保持安静、不要随意离开安全点，等待下一次官方更新。",
        },
        "take_gate_now": {
            "tone": "success",
            "headline": "主出口窗口已打开",
            "summary": "北门当前存在可执行窗口，可以尝试低暴露通过。",
            "detail": "主出口路线：{route_gate}",
            "route_label": "主出口建议",
            "route_value": "抓窗口快速通过，避免在北门外停留",
            "coach_title": "突围建议",
            "coach_body": "守卫视线已松动，保持直线移动，不要在门口犹豫。",
        },
        "distract_guard": {
            "tone": "danger",
            "headline": "主出口还不安全，先制造位移",
            "summary": "北门守卫仍覆盖出口线，直接尝试主出口风险过高。",
            "detail": "当前阻断原因：{gate_reason}",
            "route_label": "主出口建议",
            "route_value": "先用瓶子或服务机器人噪声制造偏移",
            "coach_title": "牵制建议",
            "coach_body": "先把守卫从直视线拉开，再切向出口，不要硬冲。",
        },
        "relocate_to_secret": {
            "tone": "info",
            "headline": "密道条件更优，转向低暴露撤离",
            "summary": "你已经具备密道条件，当前最稳妥的路线不是正面主出口。",
            "detail": "密道路线：{route_secret}",
            "route_label": "密道建议",
            "route_value": "沿楼层内侧路线移动到密道入口",
            "coach_title": "转移建议",
            "coach_body": "别在高风险出口消耗时间，直接转向密道入口。",
        },
        "take_secret_now": {
            "tone": "success",
            "headline": "密道已解锁，立即撤离",
            "summary": "你已经到达密道关键楼层，当前应直接完成撤离。",
            "detail": "密道路线已完成，可在当前楼层迅速进入出口点。",
            "route_label": "密道建议",
            "route_value": "保持低暴露，立即进入密道出口区",
            "coach_title": "撤离建议",
            "coach_body": "线索链已齐，别再回头搜索，直接走密道。",
        },
        "steady": {
            "tone": "info",
            "headline": "保持低暴露移动并继续确认信息",
            "summary": "当前没有更优的单一步骤，继续沿低暴露路线推进即可。",
            "detail": "主出口：{route_gate}；密道：{route_secret}",
            "route_label": "当前建议",
            "route_value": "沿内侧路线移动，优先听官方更新",
            "coach_title": "移动建议",
            "coach_body": "别停在开阔区，边移动边确认地图和广播。",
        },
    },
    "en-US": {
        "backend.hf": "HF route model",
        "backend.heuristic": "local policy model",
        "map_and_plan": {
            "tone": "info",
            "headline": "Confirm the floor board before moving deeper",
            "summary": "You are still in orientation flow. Read a nearby board and confirm stairs first.",
            "detail": "Use the board to lock in your floor, stairs, and next safe route before pushing forward.",
            "route_label": "Current recommendation",
            "route_value": "Check a nearby board and build a floor plan first",
            "coach_title": "Guide advice",
            "coach_body": "Know your floor, stairs, and fallback room before you move.",
        },
        "collect_clues": {
            "tone": "warning",
            "headline": "Clues are incomplete. Keep collecting at low risk",
            "summary": "The secret route is not fully unlocked yet. Stay with low-exposure clue points.",
            "detail": "Secret route: {route_secret}",
            "route_label": "Tunnel progress",
            "route_value": "{clues_found}/{required_clues} clues. Use safer interior rooms first",
            "coach_title": "Search advice",
            "coach_body": "Use low-exposure classrooms, boards, and terminals. Do not cut through open lanes.",
        },
        "relocate_safe": {
            "tone": "danger",
            "headline": "You are exposed. Relocate before doing anything else",
            "summary": "Your current position is not a qualified shelter point.",
            "detail": "Leave glass zones, open corridors, and exit bottlenecks before choosing a route.",
            "route_label": "Current recommendation",
            "route_value": "Stabilize first, then escape",
            "coach_title": "Shelter advice",
            "coach_body": "Move to an interior room or behind strong cover before making the next decision.",
        },
        "hold_for_police": {
            "tone": "success",
            "headline": "Current room is viable. Hold for police arrival",
            "summary": "You are already in a qualified space and can wait out the remaining timer.",
            "detail": "Police ETA: {remaining}s. Stay low exposure unless official updates say otherwise.",
            "route_label": "Current recommendation",
            "route_value": "Stay in place and monitor official updates",
            "coach_title": "Hold advice",
            "coach_body": "Stay quiet, stay inside, and avoid unnecessary movement.",
        },
        "take_gate_now": {
            "tone": "success",
            "headline": "Main gate has a usable window",
            "summary": "The north gate is currently viable. Move through with low exposure.",
            "detail": "Main gate route: {route_gate}",
            "route_label": "Gate recommendation",
            "route_value": "Commit and move through the window quickly",
            "coach_title": "Breakout advice",
            "coach_body": "The guard line is loose enough. Commit to the movement and do not hesitate at the door.",
        },
        "distract_guard": {
            "tone": "danger",
            "headline": "Do not force the main gate yet",
            "summary": "The guard still controls the gate line. Create displacement first.",
            "detail": "Current block: {gate_reason}",
            "route_label": "Gate recommendation",
            "route_value": "Use a bottle or service-bot noise before trying again",
            "coach_title": "Distraction advice",
            "coach_body": "Pull the guard off the direct line first, then cut through the gate.",
        },
        "relocate_to_secret": {
            "tone": "info",
            "headline": "The secret route is now stronger than the gate",
            "summary": "You already meet the tunnel condition. Shift to the lower-exposure route.",
            "detail": "Secret route: {route_secret}",
            "route_label": "Tunnel recommendation",
            "route_value": "Move through interior connections toward the tunnel",
            "coach_title": "Relocation advice",
            "coach_body": "Stop spending time near the exposed exit. Transition to the tunnel route.",
        },
        "take_secret_now": {
            "tone": "success",
            "headline": "Tunnel is unlocked. Leave now",
            "summary": "You are already on the tunnel floor. Finish the escape instead of continuing to search.",
            "detail": "Tunnel route is complete. Use the current floor exit path immediately.",
            "route_label": "Tunnel recommendation",
            "route_value": "Stay low exposure and enter the tunnel zone now",
            "coach_title": "Escape advice",
            "coach_body": "Clue chain is complete. Do not loop back. Finish the tunnel escape.",
        },
        "steady": {
            "tone": "info",
            "headline": "Keep moving low-exposure and keep checking official info",
            "summary": "There is no sharper single action yet. Continue with interior movement and awareness.",
            "detail": "Gate: {route_gate}; Tunnel: {route_secret}",
            "route_label": "Current recommendation",
            "route_value": "Use interior movement and stay synced with alerts",
            "coach_title": "Movement advice",
            "coach_body": "Do not idle in open space. Move while checking boards and broadcasts.",
        },
    },
}


class CampusAdvisor:
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self._fallback = _HeuristicAdvisorBackend()
        self._hf = _OptionalHFAdvisorBackend()

    def evaluate(self, language: str, payload: dict[str, Any]) -> AdvisoryDecision:
        strategy = self._fallback.choose_strategy(payload)
        hf_strategy = self._hf.choose_strategy(payload)
        if hf_strategy:
            strategy = hf_strategy
        locale = language if language in _TEMPLATES else "en-US"
        bundle = _TEMPLATES[locale][strategy]
        backend_key = "backend.hf" if hf_strategy else "backend.heuristic"
        remaining = max(0, payload["survive_seconds"] - int(payload["alert_elapsed"]))
        gate_reason = payload["gate_reason_text"] or payload["default_gate_reason"]
        route_secret = payload["route_secret"] or payload["default_route_unknown"]
        route_gate = payload["route_gate"] or payload["default_route_unknown"]
        fmt = {
            "clues_found": payload["clues_found"],
            "required_clues": payload["required_clues"],
            "route_secret": route_secret,
            "route_gate": route_gate,
            "gate_reason": gate_reason,
            "remaining": remaining,
        }
        return AdvisoryDecision(
            strategy=strategy,
            tone=str(bundle["tone"]),
            headline=str(bundle["headline"]).format(**fmt),
            summary=str(bundle["summary"]).format(**fmt),
            detail=str(bundle["detail"]).format(**fmt),
            route_label=str(bundle["route_label"]).format(**fmt),
            route_value=str(bundle["route_value"]).format(**fmt),
            coach_title=str(bundle["coach_title"]).format(**fmt),
            coach_body=str(bundle["coach_body"]).format(**fmt),
            backend_label=str(_TEMPLATES[locale][backend_key]),
        )

    def backend_name(self) -> str:
        if self._hf.available:
            return f"hf:{self._hf.model_id}"
        return self._fallback.name
