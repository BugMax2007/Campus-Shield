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

var data: Dictionary = {}
var world_size: Vector2 = Vector2(3200, 2240)
var rooms: Array[Dictionary] = []
var walls: Array[Rect2] = []
var cover: Array[Rect2] = []
var exits: Array[Dictionary] = []
var signage: Array[Dictionary] = []

func setup(level_data: Dictionary) -> void:
	data = level_data
	world_size = level_data.get("world_size", world_size)
	rooms = level_data.get("rooms", [])
	walls = level_data.get("walls", [])
	cover = level_data.get("cover", [])
	exits = level_data.get("exits", [])
	signage = level_data.get("signage", [])
	queue_redraw()


func spawn_position(spawn_id: String) -> Vector2:
	var spawns: Dictionary = data.get("spawns", {})
	return spawns.get(spawn_id, Vector2(550, 1260))


func point_blocked(point: Vector2, radius: float) -> bool:
	var probe: Rect2 = Rect2(point - Vector2(radius, radius), Vector2(radius * 2.0, radius * 2.0))
	for rect: Rect2 in walls:
		if probe.intersects(rect):
			return true
	for rect: Rect2 in cover:
		if probe.intersects(rect):
			return true
	return false


func line_blocked(start: Vector2, end: Vector2) -> bool:
	for rect: Rect2 in walls:
		if _segment_intersects_rect(start, end, rect):
			return true
	for rect: Rect2 in cover:
		if _segment_intersects_rect(start, end, rect):
			return true
	return false


func room_at(point: Vector2) -> Dictionary:
	for room: Dictionary in rooms:
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
		var rect: Rect2 = exit_data["rect"]
		if rect.has_point(point):
			return exit_data
	return {}


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, world_size), COLOR_GRASS)
	draw_rect(Rect2(150, 190, 2520, 1440), COLOR_WALKWAY)
	for room: Dictionary in rooms:
		var rect: Rect2 = room["rect"]
		var color: Color = COLOR_SAFE if str(room.get("risk_level", "")) == "safe" else COLOR_RISK
		draw_rect(rect, color)
		draw_rect(rect, COLOR_WALL, false, 5.0)
		_draw_label(str(room.get("name", "")), rect.position + Vector2(18, 34), 18)
	for rect: Rect2 in cover:
		draw_rect(rect, COLOR_COVER)
	for rect: Rect2 in walls:
		draw_rect(rect, COLOR_WALL)
	for exit_data: Dictionary in exits:
		var exit_rect: Rect2 = exit_data["rect"]
		draw_rect(exit_rect, COLOR_SIGN, false, 5.0)
		_draw_label(str(exit_data.get("id", "exit")), exit_rect.position + Vector2(12, 36), 16)
	for sign: Dictionary in signage:
		var sign_rect: Rect2 = sign["rect"]
		draw_rect(sign_rect, COLOR_SIGN)
		_draw_label(str(sign.get("label", "Sign")), sign_rect.position + Vector2(8, 30), 14)


func _draw_label(text: String, pos: Vector2, size: int) -> void:
	draw_string(ThemeDB.fallback_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, COLOR_TEXT)


func _segment_intersects_rect(a: Vector2, b: Vector2, rect: Rect2) -> bool:
	var steps: int = max(4, int(a.distance_to(b) / 16.0))
	for index: int in range(steps + 1):
		var point: Vector2 = a.lerp(b, float(index) / float(steps))
		if rect.has_point(point):
			return true
	return false
