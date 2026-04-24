class_name LevelLoader
extends RefCounted

const REQUIRED_LAYERS: Array[String] = [
	"ground",
	"walls",
	"cover",
	"rooms",
	"interactables",
	"spawns",
	"patrol_paths",
	"exits",
	"signage",
	"actors",
]

func load_level(path: String) -> Dictionary:
	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Cannot open level JSON: %s" % path)
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Invalid level JSON: %s" % path)
		return {}
	var raw: Dictionary = parsed as Dictionary
	var layers: Dictionary = _layers_by_name(raw)
	for layer_name: String in REQUIRED_LAYERS:
		if not layers.has(layer_name):
			push_error("Missing required Tiled layer: %s" % layer_name)
			return {}

	var tile_width: float = float(raw.get("tilewidth", 32))
	var tile_height: float = float(raw.get("tileheight", 32))
	var data: Dictionary = {
		"world_size": Vector2(float(raw.get("width", 100)) * tile_width, float(raw.get("height", 70)) * tile_height),
		"rooms": _parse_rooms(layers["rooms"]),
		"walls": _parse_rect_layer(layers["walls"]),
		"wall_details": _parse_named_rect_layer(layers["walls"]),
		"cover": _parse_rect_layer(layers["cover"]),
		"cover_details": _parse_named_rect_layer(layers["cover"]),
		"interactables": _parse_interactables(layers["interactables"]),
		"spawns": _parse_spawns(layers["spawns"]),
		"patrol_paths": _parse_patrol_paths(layers["patrol_paths"]),
		"exits": _parse_exits(layers["exits"]),
		"signage": _parse_signage(layers["signage"]),
		"actors": _parse_actors(layers["actors"]),
	}
	return data


func _layers_by_name(raw: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for layer_value: Variant in raw.get("layers", []):
		var layer: Dictionary = layer_value as Dictionary
		result[str(layer.get("name", ""))] = layer
	return result


func _parse_rooms(layer: Dictionary) -> Array[Dictionary]:
	var rooms: Array[Dictionary] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		_require_props(props, ["room_id", "room_name", "risk_level", "safe_tags"], "room")
		rooms.append({
			"id": str(props["room_id"]),
			"name": str(props["room_name"]),
			"risk_level": str(props["risk_level"]),
			"safe_tags": _split_tags(str(props["safe_tags"])),
			"rect": _rect(obj),
		})
	return rooms


func _parse_rect_layer(layer: Dictionary) -> Array[Rect2]:
	var rects: Array[Rect2] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		rects.append(_rect(obj))
	return rects


func _parse_named_rect_layer(layer: Dictionary) -> Array[Dictionary]:
	var items: Array[Dictionary] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		items.append({
			"name": str(obj.get("name", "")),
			"type": str(obj.get("type", "")),
			"rect": _rect(obj),
		})
	return items


func _parse_interactables(layer: Dictionary) -> Array[Dictionary]:
	var items: Array[Dictionary] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		_require_props(props, ["interaction_id", "interaction_type", "label", "education_key"], "interactable")
		var rect: Rect2 = _rect(obj)
		items.append({
			"id": str(props["interaction_id"]),
			"type": str(props["interaction_type"]),
			"label": str(props["label"]),
			"education_key": str(props["education_key"]),
			"effect_type": str(props.get("effect_type", props["interaction_type"])),
			"required_phase": str(props.get("required_phase", "any")),
			"route_value": str(props.get("route_value", "")),
			"feedback_key": str(props.get("feedback_key", "")),
			"once": bool(props.get("once", true)),
			"rect": rect,
			"position": rect.get_center(),
		})
	return items


func _parse_spawns(layer: Dictionary) -> Dictionary:
	var spawns: Dictionary = {}
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		_require_props(props, ["spawn_id"], "spawn")
		spawns[str(props["spawn_id"])] = _rect(obj).get_center()
	return spawns


func _parse_patrol_paths(layer: Dictionary) -> Dictionary:
	var paths: Dictionary = {}
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		_require_props(props, ["patrol_id", "raider_role", "path_points"], "patrol_path")
		var origin: Vector2 = Vector2(float(obj.get("x", 0)), float(obj.get("y", 0)))
		var points: Array[Vector2] = []
		if obj.has("polyline"):
			for point_value: Variant in obj.get("polyline", []):
				var point: Dictionary = point_value as Dictionary
				points.append(origin + Vector2(float(point.get("x", 0)), float(point.get("y", 0))))
		else:
			points = _parse_point_string(origin, str(props["path_points"]))
		paths[str(props["patrol_id"])] = {
			"id": str(props["patrol_id"]),
			"role": str(props["raider_role"]),
			"points": points,
		}
	return paths


func _parse_exits(layer: Dictionary) -> Array[Dictionary]:
	var exits: Array[Dictionary] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		_require_props(props, ["exit_id", "exit_type", "required_clues", "blocked_by"], "exit")
		exits.append({
			"id": str(props["exit_id"]),
			"type": str(props["exit_type"]),
			"required_clues": int(props["required_clues"]),
			"blocked_by": str(props["blocked_by"]),
			"rect": _rect(obj),
		})
	return exits


func _parse_signage(layer: Dictionary) -> Array[Dictionary]:
	var signs: Array[Dictionary] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		signs.append({
			"label": str(props.get("label", obj.get("name", "Sign"))),
			"rect": _rect(obj),
		})
	return signs


func _parse_actors(layer: Dictionary) -> Array[Dictionary]:
	var actors: Array[Dictionary] = []
	for obj_value: Variant in layer.get("objects", []):
		var obj: Dictionary = obj_value as Dictionary
		var props: Dictionary = _props(obj)
		_require_props(props, ["actor_id", "actor_kind", "actor_role"], "actor")
		actors.append({
			"id": str(props["actor_id"]),
			"kind": str(props["actor_kind"]),
			"role": str(props["actor_role"]),
			"label": str(props.get("label", props["actor_id"])),
			"patrol_id": str(props.get("patrol_id", "")),
			"position": _rect(obj).get_center(),
		})
	return actors


func _props(obj: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for prop_value: Variant in obj.get("properties", []):
		var prop: Dictionary = prop_value as Dictionary
		result[str(prop.get("name", ""))] = prop.get("value", "")
	return result


func _rect(obj: Dictionary) -> Rect2:
	return Rect2(
		float(obj.get("x", 0)),
		float(obj.get("y", 0)),
		float(obj.get("width", 1)),
		float(obj.get("height", 1))
	)


func _split_tags(raw: String) -> Array[String]:
	var tags: Array[String] = []
	for tag: String in raw.split(",", false):
		tags.append(tag.strip_edges())
	return tags


func _parse_point_string(origin: Vector2, raw: String) -> Array[Vector2]:
	var points: Array[Vector2] = []
	for pair: String in raw.split(" ", false):
		var xy: PackedStringArray = pair.split(",", false)
		if xy.size() == 2:
			points.append(origin + Vector2(float(xy[0]), float(xy[1])))
	return points


func _require_props(props: Dictionary, names: Array[String], context: String) -> void:
	for name: String in names:
		if not props.has(name):
			push_error("Missing %s property: %s" % [context, name])
