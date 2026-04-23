class_name Robot
extends Node2D

signal hint_requested(message: String)
signal noise_created(position: Vector2)

var actor_id: String = ""
var role: String = "guide"
var label: String = "Robot"
var home: Vector2 = Vector2.ZERO
var hint_cooldown: float = 0.0
var noise_timer: float = 8.0

func setup(actor: Dictionary) -> void:
	actor_id = str(actor.get("id", "robot"))
	role = str(actor.get("role", "guide"))
	label = str(actor.get("label", actor_id))
	position = actor.get("position", Vector2.ZERO)
	home = position
	hint_cooldown = 0.0
	noise_timer = 8.0


func tick(delta: float, player_position: Vector2, phase: String) -> void:
	position = home + Vector2(cos(Time.get_ticks_msec() / 900.0), sin(Time.get_ticks_msec() / 1200.0)) * 18.0
	if hint_cooldown > 0.0:
		hint_cooldown -= delta
	if position.distance_to(player_position) < 120.0 and hint_cooldown <= 0.0:
		hint_requested.emit(_hint_for_phase(phase))
		hint_cooldown = 9.0
	if role == "service_noise" and phase == "Alert":
		noise_timer -= delta
		if noise_timer <= 0.0:
			noise_timer = 14.0
			noise_created.emit(position)


func _hint_for_phase(phase: String) -> String:
	if role == "guide":
		return "导览机器人：先找地图板确认位置，不要靠猜测探索。"
	if role == "security":
		return "安保机器人：如果附近有巡逻，优先降低暴露并进入可遮挡路线。"
	if phase == "Alert":
		return "服务机器人：移动噪声可能短暂改变搜索方向。"
	return "服务机器人：服务通道标识通常在后勤区域附近。"


func _draw() -> void:
	draw_rect(Rect2(-16, -16, 32, 32), Color8(61, 170, 184))
	draw_rect(Rect2(-16, -16, 32, 32), Color8(224, 246, 249), false, 3.0)
	draw_circle(Vector2(-6, -3), 3.0, Color8(235, 247, 247))
	draw_circle(Vector2(6, -3), 3.0, Color8(235, 247, 247))
