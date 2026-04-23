class_name Player
extends Node2D

signal noise_created(position: Vector2)

var level
var radius: float = 18.0
var speed: float = 270.0
var facing: Vector2 = Vector2.RIGHT
var bottles: int = 3
var enabled: bool = false

func setup(active_level, spawn: Vector2) -> void:
	level = active_level
	position = spawn
	facing = Vector2.RIGHT
	bottles = 3
	enabled = false
	queue_redraw()


func tick(delta: float) -> void:
	if not enabled:
		return
	var input_dir: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if input_dir.length() <= 0.0:
		return
	facing = input_dir.normalized()
	var move: Vector2 = facing * speed * delta
	_move_axis(Vector2(move.x, 0.0))
	_move_axis(Vector2(0.0, move.y))
	queue_redraw()


func throw_bottle() -> bool:
	if bottles <= 0:
		return false
	bottles -= 1
	var noise_position: Vector2 = position + facing.normalized() * 210.0
	noise_created.emit(noise_position)
	return true


func _move_axis(delta_pos: Vector2) -> void:
	var next_position: Vector2 = position + delta_pos
	if level != null and level.point_blocked(next_position, radius):
		return
	position = next_position.clamp(Vector2(90, 90), level.world_size - Vector2(90, 90))


func _draw() -> void:
	draw_circle(Vector2.ZERO, radius, Color8(42, 135, 199))
	draw_circle(Vector2.ZERO, radius, Color8(237, 246, 252), false, 3.0)
	draw_line(Vector2.ZERO, facing.normalized() * 28.0, Color8(237, 246, 252), 4.0)
