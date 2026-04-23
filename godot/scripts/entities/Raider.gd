class_name Raider
extends Node2D

signal player_seen(raider_id: String)
signal player_caught(raider_id: String)

const STATE_PATROL := "Patrol"
const STATE_INVESTIGATE := "InvestigateNoise"
const STATE_SEARCH := "Search"
const STATE_CHASE := "Chase"
const STATE_RETURN := "Return"

var actor_id: String = ""
var role: String = "patrol"
var state: String = STATE_PATROL
var patrol_points: Array[Vector2] = []
var patrol_index: int = 0
var heading: Vector2 = Vector2.RIGHT
var last_seen: Vector2 = Vector2.ZERO
var search_timer: float = 0.0
var speed: float = 140.0
var sight_range: float = 360.0
var sight_angle: float = 70.0
var hearing_range: float = 285.0
var level

func setup(actor: Dictionary, path: Dictionary, active_level) -> void:
	actor_id = str(actor.get("id", "raider"))
	role = str(actor.get("role", "patrol"))
	position = actor.get("position", Vector2.ZERO)
	last_seen = position
	level = active_level
	patrol_points = path.get("points", [])
	if patrol_points.is_empty():
		patrol_points = [position]
	state = STATE_PATROL
	patrol_index = 0
	heading = Vector2.RIGHT
	search_timer = 0.0
	speed = 125.0 if role == "guard" else 148.0


func tick(delta: float, player_position: Vector2, phase: String, noises: Array[Dictionary]) -> void:
	if phase != "Alert":
		_follow_patrol(delta)
		queue_redraw()
		return
	if _can_see_player(player_position):
		state = STATE_CHASE
		last_seen = player_position
		search_timer = 7.0
		player_seen.emit(actor_id)
	elif state == STATE_CHASE and position.distance_to(player_position) > 520.0:
		state = STATE_SEARCH
		search_timer = 6.0
	elif state == STATE_SEARCH:
		search_timer -= delta
		if search_timer <= 0.0:
			state = STATE_RETURN
	elif state == STATE_INVESTIGATE:
		search_timer -= delta
		if search_timer <= 0.0:
			state = STATE_SEARCH
			search_timer = 4.0

	if state not in [STATE_CHASE, STATE_SEARCH]:
		for noise: Dictionary in noises:
			var noise_pos: Vector2 = noise.get("position", Vector2.ZERO)
			if position.distance_to(noise_pos) <= hearing_range:
				state = STATE_INVESTIGATE
				last_seen = noise_pos
				search_timer = 4.0
				break

	var target: Vector2 = _target_for_state(player_position)
	_move_toward(target, delta)
	if phase == "Alert" and position.distance_to(player_position) < 32.0:
		player_caught.emit(actor_id)
	queue_redraw()


func _target_for_state(player_position: Vector2) -> Vector2:
	if state == STATE_CHASE:
		return player_position
	if state in [STATE_INVESTIGATE, STATE_SEARCH]:
		return last_seen
	if state == STATE_RETURN and not patrol_points.is_empty():
		if position.distance_to(patrol_points[patrol_index]) < 26.0:
			state = STATE_PATROL
		return patrol_points[patrol_index]
	return _patrol_target()


func _patrol_target() -> Vector2:
	if patrol_points.is_empty():
		return position
	var target: Vector2 = patrol_points[patrol_index]
	if position.distance_to(target) < 22.0:
		patrol_index = (patrol_index + 1) % patrol_points.size()
		target = patrol_points[patrol_index]
	return target


func _follow_patrol(delta: float) -> void:
	_move_toward(_patrol_target(), delta)


func _move_toward(target: Vector2, delta: float) -> void:
	var delta_vec: Vector2 = target - position
	if delta_vec.length() <= 1.0:
		return
	heading = delta_vec.normalized()
	var step: Vector2 = heading * speed * delta
	var next_position: Vector2 = position + step
	if level == null or not level.point_blocked(next_position, 16.0):
		position = next_position
		return
	var side: Vector2 = Vector2(-heading.y, heading.x) * speed * delta
	if level != null and not level.point_blocked(position + side, 16.0):
		position += side


func _can_see_player(player_position: Vector2) -> bool:
	var to_player: Vector2 = player_position - position
	if to_player.length() > sight_range:
		return false
	if to_player.length() <= 1.0:
		return true
	var angle: float = abs(rad_to_deg(heading.normalized().angle_to(to_player.normalized())))
	if angle > sight_angle * 0.5:
		return false
	return level == null or not level.line_blocked(position, player_position)


func _draw() -> void:
	var left: Vector2 = heading.rotated(deg_to_rad(-sight_angle * 0.5)).normalized() * sight_range
	var right: Vector2 = heading.rotated(deg_to_rad(sight_angle * 0.5)).normalized() * sight_range
	draw_colored_polygon(PackedVector2Array([Vector2.ZERO, left, right]), Color(0.86, 0.12, 0.10, 0.12))
	draw_circle(Vector2.ZERO, 18.0, Color8(166, 68, 70))
	draw_circle(Vector2.ZERO, 18.0, Color8(87, 33, 36), false, 3.0)
	draw_string(ThemeDB.fallback_font, Vector2(-28, -26), state, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color8(250, 246, 240))
