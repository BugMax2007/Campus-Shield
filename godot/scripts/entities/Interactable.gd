class_name Interactable
extends Node2D

var data: Dictionary = {}
var radius: float = 80.0
var found: bool = false
var highlighted: bool = false
var floor_id: String = "1F"

func setup(interactable_data: Dictionary) -> void:
	data = interactable_data
	position = interactable_data.get("position", Vector2.ZERO)
	floor_id = str(interactable_data.get("floor_id", "1F"))
	found = false
	queue_redraw()


func is_near(point: Vector2) -> bool:
	return position.distance_to(point) <= radius


func label() -> String:
	return str(data.get("label", "Interact"))


func interaction_type() -> String:
	return str(data.get("type", "unknown"))


func mark_found() -> void:
	found = true
	queue_redraw()


func set_highlighted(value: bool) -> void:
	if highlighted == value:
		return
	highlighted = value
	queue_redraw()


func _draw() -> void:
	if found and interaction_type() == "clue":
		return
	var fill: Color = Color8(238, 189, 61)
	if interaction_type() == "clue":
		fill = Color8(92, 157, 115)
	elif interaction_type() == "official_notice":
		fill = Color8(62, 132, 184)
	elif interaction_type() == "support_phone":
		fill = Color8(57, 102, 201)
	elif interaction_type() == "npc":
		fill = Color8(182, 122, 55)
	elif interaction_type() == "stair":
		fill = Color8(86, 92, 184)
	elif interaction_type() == "hide_spot":
		fill = Color8(55, 92, 82)
	elif interaction_type() in ["keycard", "access_panel"]:
		fill = Color8(174, 124, 202)
	if highlighted:
		var pulse: float = 4.0 + sin(Time.get_ticks_msec() / 220.0) * 2.0
		draw_circle(Vector2.ZERO, 31.0 + pulse, Color(fill.r, fill.g, fill.b, 0.20))
		draw_circle(Vector2.ZERO, 30.0 + pulse, fill, false, 4.0)
	draw_circle(Vector2.ZERO, 17.0, fill)
	draw_circle(Vector2.ZERO, 17.0, Color8(248, 244, 232), false, 3.0)
	draw_string(ThemeDB.fallback_font, Vector2(-18, 34), _short_label(), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color8(24, 38, 52))
	if highlighted:
		draw_string(ThemeDB.fallback_font, Vector2(-34, -34), "目标", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color8(24, 38, 52))


func _short_label() -> String:
	match interaction_type():
		"map_board":
			return "MAP"
		"clue":
			return "CLUE"
		"official_notice":
			return "ALERT"
		"door_lock":
			return "LOCK"
		"support_phone":
			return "HELP"
		"npc":
			return "NPC"
		"stair":
			return "STAIR"
		"hide_spot":
			return "HIDE"
		"keycard":
			return "CARD"
		"access_panel":
			return "PANEL"
		"broadcast":
			return "PA"
	return "INFO"
