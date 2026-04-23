class_name MapGuide
extends Control

var level_data: Dictionary = {}
var player_position: Vector2 = Vector2.ZERO

func update_map(data: Dictionary, pos: Vector2) -> void:
	level_data = data
	player_position = pos
	queue_redraw()


func _draw() -> void:
	if level_data.is_empty():
		return
	var world_size: Vector2 = level_data.get("world_size", Vector2(3200, 2240))
	var bounds: Rect2 = Rect2(Vector2(18, 18), size - Vector2(36, 36))
	draw_rect(bounds, Color8(226, 232, 220))
	draw_rect(bounds, Color8(69, 91, 106), false, 3.0)
	var scale: float = min(bounds.size.x / world_size.x, bounds.size.y / world_size.y)
	var origin: Vector2 = bounds.position + Vector2(12, 12)
	for room: Dictionary in level_data.get("rooms", []):
		var rect: Rect2 = room["rect"]
		var mapped: Rect2 = Rect2(origin + rect.position * scale, rect.size * scale)
		var color: Color = Color8(196, 225, 204) if str(room.get("risk_level", "")) == "safe" else Color8(232, 198, 190)
		draw_rect(mapped, color)
		draw_rect(mapped, Color8(69, 91, 106), false, 2.0)
	for exit_data: Dictionary in level_data.get("exits", []):
		var exit_rect: Rect2 = exit_data["rect"]
		draw_rect(Rect2(origin + exit_rect.position * scale, exit_rect.size * scale), Color8(238, 189, 61), false, 3.0)
	draw_circle(origin + player_position * scale, 7.0, Color8(42, 135, 199))
	draw_string(ThemeDB.fallback_font, origin + player_position * scale + Vector2(10, -8), "You are here", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color8(24, 38, 52))
