class_name Interactable
extends Node2D

var data: Dictionary = {}
var radius: float = 80.0
var found: bool = false

func setup(interactable_data: Dictionary) -> void:
	data = interactable_data
	position = interactable_data.get("position", Vector2.ZERO)
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
	draw_circle(Vector2.ZERO, 17.0, fill)
	draw_circle(Vector2.ZERO, 17.0, Color8(248, 244, 232), false, 3.0)
	draw_string(ThemeDB.fallback_font, Vector2(-18, 34), _short_label(), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color8(24, 38, 52))


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
	return "INFO"
