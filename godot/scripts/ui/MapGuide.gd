class_name MapGuide
extends Control

var level_data: Dictionary = {}
var player_position: Vector2 = Vector2.ZERO
var current_floor: String = "1F"

func update_map(data: Dictionary, pos: Vector2, floor_id: String = "1F") -> void:
	level_data = data
	player_position = pos
	current_floor = floor_id
	queue_redraw()


func _draw() -> void:
	if level_data.is_empty():
		return
	var world_size: Vector2 = level_data.get("world_size", Vector2(3200, 2240))
	var bounds: Rect2 = Rect2(Vector2(18, 18), size - Vector2(36, 36))
	draw_rect(bounds, Color8(226, 232, 220))
	draw_rect(bounds, Color8(69, 91, 106), false, 3.0)
	draw_string(ThemeDB.fallback_font, bounds.position + Vector2(16, 26), "Chapter 01 / Library + Student Center / %s" % current_floor, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color8(24, 38, 52))
	var map_rect: Rect2 = Rect2(bounds.position + Vector2(16, 42), bounds.size - Vector2(32, 74))
	var scale: float = min(map_rect.size.x / world_size.x, map_rect.size.y / world_size.y)
	var scaled_size: Vector2 = world_size * scale
	var origin: Vector2 = map_rect.position + (map_rect.size - scaled_size) * 0.5
	draw_rect(Rect2(origin, scaled_size), Color8(191, 204, 190), true)
	for room: Dictionary in level_data.get("rooms", []):
		if str(room.get("floor_id", "1F")) != current_floor:
			continue
		var rect: Rect2 = room["rect"]
		var mapped: Rect2 = Rect2(origin + rect.position * scale, rect.size * scale)
		var color: Color = Color8(196, 225, 204) if str(room.get("risk_level", "")) == "safe" else Color8(232, 198, 190)
		draw_rect(mapped, color)
		draw_rect(mapped, Color8(69, 91, 106), false, 2.0)
		if mapped.size.x > 80 and mapped.size.y > 34:
			draw_string(ThemeDB.fallback_font, mapped.position + Vector2(8, 19), str(room.get("name", "")), HORIZONTAL_ALIGNMENT_LEFT, mapped.size.x - 12, 11, Color8(24, 38, 52))
	for item: Dictionary in level_data.get("cover_details", []):
		if str(item.get("floor_id", "1F")) != current_floor:
			continue
		var rect: Rect2 = item["rect"]
		var cover_rect: Rect2 = Rect2(origin + rect.position * scale, rect.size * scale)
		draw_rect(cover_rect, Color8(122, 88, 55))
	for item: Dictionary in level_data.get("wall_details", []):
		if str(item.get("floor_id", "1F")) != current_floor:
			continue
		var rect: Rect2 = item["rect"]
		var wall_rect: Rect2 = Rect2(origin + rect.position * scale, rect.size * scale)
		draw_rect(wall_rect, Color8(43, 61, 75))
	for exit_data: Dictionary in level_data.get("exits", []):
		if str(exit_data.get("floor_id", "1F")) != current_floor:
			continue
		var exit_rect: Rect2 = exit_data["rect"]
		var mapped_exit: Rect2 = Rect2(origin + exit_rect.position * scale, exit_rect.size * scale)
		draw_rect(mapped_exit, Color8(238, 189, 61), false, 4.0)
		draw_string(ThemeDB.fallback_font, mapped_exit.position + Vector2(4, -5), str(exit_data.get("type", "exit")).to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color8(24, 38, 52))
	var player_dot: Vector2 = origin + player_position * scale
	draw_circle(player_dot, 10.0, Color8(255, 255, 247))
	draw_circle(player_dot, 7.0, Color8(42, 135, 199))
	draw_string(ThemeDB.fallback_font, player_dot + Vector2(12, -10), "You are here", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color8(24, 38, 52))
	_draw_legend(bounds)


func _draw_legend(bounds: Rect2) -> void:
	var y: float = bounds.end.y - 18
	var x: float = bounds.position.x + 18
	_draw_legend_item(Vector2(x, y), Color8(196, 225, 204), "合格避险")
	_draw_legend_item(Vector2(x + 130, y), Color8(232, 198, 190), "高暴露")
	_draw_legend_item(Vector2(x + 245, y), Color8(122, 88, 55), "遮挡/书架")
	_draw_legend_item(Vector2(x + 380, y), Color8(238, 189, 61), "出口/导视")


func _draw_legend_item(pos: Vector2, color: Color, text: String) -> void:
	draw_rect(Rect2(pos + Vector2(0, -12), Vector2(18, 12)), color)
	draw_rect(Rect2(pos + Vector2(0, -12), Vector2(18, 12)), Color8(69, 91, 106), false, 1.0)
	draw_string(ThemeDB.fallback_font, pos + Vector2(24, 0), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color8(24, 38, 52))
