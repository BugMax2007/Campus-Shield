# Development Rules

## Non-negotiable Product Rules

- Keep the game educational. Do not add graphic violence, weapon details, or attacker-centered mechanics.
- Do not reward risky curiosity after the alert begins.
- NPC help must stay low-risk. Allow warning, guiding, or checking official information together. Do not require heroics or direct confrontation.
- Every new interaction must teach a concrete campus safety concept, change navigation, or change state. Decorative interactions do not enter v1.
- Safety guidance in content must stay aligned with public official sources and remain clearly labeled as educational rather than authoritative instructions.

## UI Review Rules For Every Task

- Check the build at `1280x720`, `1600x900`, and `1920x1080`.
- Verify the anchor layout stays fixed: objective top-left, alert top-center, minimap top-right, prompt bottom-center, subtitles bottom-left, modal centered.
- Keep all critical text and buttons outside the outer 5% margin.
- Ensure Chinese primary text fits without truncation and English secondary text stays readable within two lines.
- Verify keyboard-only control on title, pause, phone, map, and debrief screens.
- Confirm that interactables expose all four signals: visual object, proximity prompt, icon, and label.
- Run `PYTHONPATH=src SDL_VIDEODRIVER=dummy python3 tools/render_ui_snapshots.py` after UI changes and inspect the exported screens.

## Engineering Rules

- Keep rules data-driven. Do not hardcode zone-specific outcomes inside rendering code.
- Put gameplay rules behind testable Python helpers.
- Keep save data small and deterministic.
- New features ship with at least one automated check and one manual review item.
- Use stable localization keys and do not inline player-facing strings in gameplay logic.
- Use the root-level `.codex-task-gate.md` before marking any module complete.

## Manual QA Checklist

- Complete one standard success route.
- Trigger one recoverable mistake and confirm debrief explains it.
- Trigger one failure route and confirm the reason is abstract, not graphic.
- Open phone, map, pause, and debrief at all supported resolutions.
- Confirm unlocked terms persist after restart.
