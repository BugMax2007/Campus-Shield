class_name Level
extends Node2D

const COLOR_GRASS := Color8(77, 117, 91)
const COLOR_WALKWAY := Color8(192, 202, 191)
const COLOR_WALL := Color8(43, 61, 75)
const COLOR_COVER := Color8(91, 83, 70)
const COLOR_SAFE := Color8(204, 229, 214)
const COLOR_RISK := Color8(232, 199, 190)
const COLOR_SIGN := Color8(238, 189, 61)
const COLOR_TEXT := Color8(22, 36, 50)
const COLOR_BOOK := Color8(121, 78, 49)
const COLOR_TABLE := Color8(138, 111, 82)
const COLOR_GLASS := Color8(112, 166, 185)

var data: Dictionary = {}
var world_size: Vector2 = Vector2(3200, 2240)
var rooms: Array[Dictionary] = []
var walls: Array[Rect2] = []
var cover: Array[Rect2] = []
var cover_details: Array[Dictionary] = []
var exits: Array[Dictionary] = []
var signage: Array[Dictionary] = []
var active_exit_types: Array[String] = []
var current_floor: String = "1F"

func setup(level_data: Dictionary) -> void:
	data = level_data
	world_size = level_data.get("world_size", world_size)
	rooms = level_data.get("rooms", [])
	walls = level_data.get("walls", [])
	cover = level_data.get("cover", [])
	cover_details = level_data.get("cover_details", [])
	exits = level_data.get("exits", [])
	signage = level_data.get("signage", [])
	queue_redraw()


func set_floor(floor_id: String) -> void:
	if current_floor == floor_id:
		return
	current_floor = floor_id
	queue_redraw()


func spawn_position(spawn_id: String) -> Vector2:
	var spawns: Dictionary = data.get("spawns", {})
	var spawn = spawns.get(spawn_id, {})
	if spawn is Dictionary:
		return spawn.get("position", Vector2(550, 1260))
	return spawn


func spawn_floor(spawn_id: String) -> String:
	var spawns: Dictionary = data.get("spawns", {})
	var spawn = spawns.get(spawn_id, {})
	if spawn is Dictionary:
		return str(spawn.get("floor_id", "1F"))
	return "1F"


func point_blocked(point: Vector2, radius: float) -> bool:
	var probe: Rect2 = Rect2(point - Vector2(radius, radius), Vector2(radius * 2.0, radius * 2.0))
	for rect: Rect2 in walls:
		if not _rect_active(rect, "walls"):
			continue
		if probe.intersects(rect):
			return true
	for rect: Rect2 in cover:
		if not _rect_active(rect, "cover"):
			continue
		if probe.intersects(rect):
			return true
	return false


func line_blocked(start: Vector2, end: Vector2) -> bool:
	for rect: Rect2 in walls:
		if not _rect_active(rect, "walls"):
			continue
		if _segment_intersects_rect(start, end, rect):
			return true
	for rect: Rect2 in cover:
		if not _rect_active(rect, "cover"):
			continue
		if _segment_intersects_rect(start, end, rect):
			return true
	return false


func room_at(point: Vector2) -> Dictionary:
	for room: Dictionary in rooms:
		if str(room.get("floor_id", "1F")) != current_floor:
			continue
		var rect: Rect2 = room["rect"]
		if rect.has_point(point):
			return room
	return {}


func room_name_at(point: Vector2) -> String:
	var room: Dictionary = room_at(point)
	if room.is_empty():
		return "室外步道 / Outdoor Walkway"
	return str(room.get("name", "Unknown Room"))


func is_safe_point(point: Vector2) -> bool:
	var room: Dictionary = room_at(point)
	return not room.is_empty() and str(room.get("risk_level", "")) == "safe"


func exit_at(point: Vector2) -> Dictionary:
	for exit_data: Dictionary in exits:
		if str(exit_data.get("floor_id", "1F")) != current_floor:
			continue
		var rect: Rect2 = exit_data["rect"]
		if rect.has_point(point):
			return exit_data
	return {}


func set_active_exit_types(types: Array[String]) -> void:
	if active_exit_types == types:
		return
	active_exit_types = types
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, world_size), COLOR_GRASS)
	draw_rect(Rect2(150, 190, 2520, 1440), COLOR_WALKWAY)
	_draw_walkway_lines()
	for room: Dictionary in rooms:
		if str(room.get("floor_id", "1F")) != current_floor:
			continue
		var rect: Rect2 = room["rect"]
		var color: Color = COLOR_SAFE if str(room.get("risk_level", "")) == "safe" else COLOR_RISK
		draw_rect(rect, color)
		draw_rect(rect, COLOR_WALL, false, 5.0)
		_draw_label(str(room.get("name", "")), rect.position + Vector2(18, 34), 18)
	if cover_details.is_empty():
		for rect: Rect2 in cover:
			_draw_cover_rect(rect, "")
	else:
		for item: Dictionary in cover_details:
			if str(item.get("floor_id", "1F")) != current_floor:
				continue
			_draw_cover_rect(item["rect"], str(item.get("name", "")))
	for rect: Rect2 in walls:
		if not _rect_active(rect, "walls"):
			continue
		draw_rect(rect, COLOR_WALL)
	for exit_data: Dictionary in exits:
		if str(exit_data.get("floor_id", "1F")) != current_floor:
			continue
		var exit_rect: Rect2 = exit_data["rect"]
		var exit_type: String = str(exit_data.get("type", ""))
		var active: bool = active_exit_types.has(exit_type)
		if active:
			draw_rect(exit_rect.grow(10.0), Color(COLOR_SIGN.r, COLOR_SIGN.g, COLOR_SIGN.b, 0.22))
			draw_rect(exit_rect.grow(6.0), COLOR_SIGN, false, 4.0)
		draw_rect(exit_rect, COLOR_SIGN, false, 5.0)
		_draw_label(_exit_label(exit_data), exit_rect.position + Vector2(12, 36), 16)
	for sign: Dictionary in signage:
		if str(sign.get("floor_id", "1F")) != current_floor:
			continue
		var sign_rect: Rect2 = sign["rect"]
		draw_rect(sign_rect, COLOR_SIGN)
		_draw_label(str(sign.get("label", "Sign")), sign_rect.position + Vector2(8, 30), 14)


func _draw_walkway_lines() -> void:
	for x: int in range(220, int(world_size.x) - 300, 220):
		draw_line(Vector2(x, 220), Vector2(x, 1600), Color8(151, 166, 159, 90), 2.0)
	for y: int in range(260, 1600, 180):
		draw_line(Vector2(180, y), Vector2(2620, y), Color8(151, 166, 159, 80), 2.0)


func _draw_cover_rect(rect: Rect2, cover_name: String) -> void:
	var lowered: String = cover_name.to_lower()
	var color: Color = COLOR_BOOK if lowered.contains("shelf") else COLOR_TABLE
	if lowered.contains("booth"):
		color = COLOR_COVER
	draw_rect(rect, color)
	draw_rect(rect, COLOR_WALL, false, 2.0)
	if lowered.contains("shelf"):
		_draw_bookshelf_lines(rect)
	elif lowered.contains("table"):
		draw_line(rect.position + Vector2(10, rect.size.y * 0.5), rect.position + Vector2(rect.size.x - 10, rect.size.y * 0.5), Color8(223, 202, 151, 180), 2.0)
	if rect.size.x > 135 and rect.size.y > 30:
		var label: String = "书架" if lowered.contains("shelf") else "桌面"
		_draw_label(label, rect.position + Vector2(10, rect.size.y * 0.68), 13)


func _draw_bookshelf_lines(rect: Rect2) -> void:
	if rect.size.x >= rect.size.y:
		for x: int in range(int(rect.position.x + 12), int(rect.end.x - 6), 24):
			draw_line(Vector2(x, rect.position.y + 5), Vector2(x, rect.end.y - 5), Color8(230, 192, 104, 160), 2.0)
	else:
		for y: int in range(int(rect.position.y + 12), int(rect.end.y - 6), 24):
			draw_line(Vector2(rect.position.x + 5, y), Vector2(rect.end.x - 5, y), Color8(230, 192, 104, 160), 2.0)


func _draw_label(text: String, pos: Vector2, size: int) -> void:
	draw_string(ThemeDB.fallback_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, COLOR_TEXT)


func _rect_active(rect: Rect2, collection: String) -> bool:
	var details: Array[Dictionary] = cover_details if collection == "cover" else data.get("wall_details", [])
	for item: Dictionary in details:
		if item.get("rect", Rect2()) == rect:
			return str(item.get("floor_id", "1F")) == current_floor
	return true


func _exit_label(exit_data: Dictionary) -> String:
	if str(exit_data.get("type", "")) == "main":
		return "主出口"
	if str(exit_data.get("type", "")) == "secret":
		return "服务通道"
	return str(exit_data.get("id", "exit"))


func _segment_intersects_rect(a: Vector2, b: Vector2, rect: Rect2) -> bool:
	var steps: int = max(4, int(a.distance_to(b) / 16.0))
	for index: int in range(steps + 1):
		var point: Vector2 = a.lerp(b, float(index) / float(steps))
		if rect.has_point(point):
			return true
	return false
