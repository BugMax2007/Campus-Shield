class_name ScenarioState
extends Node

signal toast_requested(message: String)
signal finished(title: String, body: String)
signal phase_changed(phase: String)

const PHASE_OPENING := "Opening"
const PHASE_EXPLORE := "Explore"
const PHASE_ALERT := "Alert"
const PHASE_ALL_CLEAR := "AllClear"

var phase: String = PHASE_OPENING
var elapsed: float = 0.0
var alert_elapsed: float = 0.0
var alert_delay: float = 55.0
var assistance_delay: float = 180.0
var police_eta: float = 180.0
var clues_found: int = 0
var map_reads: int = 0
var official_info_read: bool = false
var door_lock_checked: bool = false
var support_phone_seen: bool = false
var ending_type: String = ""
var outcome_title: String = ""
var outcome_body: String = ""
var found_interactions: Dictionary = {}

func reset() -> void:
	phase = PHASE_OPENING
	elapsed = 0.0
	alert_elapsed = 0.0
	police_eta = assistance_delay
	clues_found = 0
	map_reads = 0
	official_info_read = false
	door_lock_checked = false
	support_phone_seen = false
	ending_type = ""
	outcome_title = ""
	outcome_body = ""
	found_interactions.clear()
	phase_changed.emit(phase)


func begin_explore() -> void:
	phase = PHASE_EXPLORE
	toast_requested.emit("导览开始：先熟悉地图板、教室门锁和官方信息来源。")
	phase_changed.emit(phase)


func tick(delta: float, player_in_safe_room: bool) -> void:
	if phase == PHASE_EXPLORE:
		elapsed += delta
		if elapsed >= alert_delay or official_info_read:
			begin_alert()
	elif phase == PHASE_ALERT:
		alert_elapsed += delta
		police_eta = max(0.0, assistance_delay - alert_elapsed)
		if police_eta <= 0.0 and player_in_safe_room:
			finish("援助到达 / Assistance Arrived", "你留在可上锁、低暴露的安全空间中，等待官方解除警报。", "wait_assistance")


func begin_alert() -> void:
	if phase == PHASE_ALERT:
		return
	phase = PHASE_ALERT
	toast_requested.emit("官方警报触发：确认信息、降低暴露、不要为了好奇返回风险区。")
	phase_changed.emit(phase)


func record_interaction(interaction: Dictionary) -> String:
	var interaction_id: String = str(interaction.get("id", ""))
	if interaction_id != "":
		found_interactions[interaction_id] = true
	var interaction_type: String = str(interaction.get("type", ""))
	match interaction_type:
		"map_board":
			map_reads += 1
			return "地图板已读取：当前位置、主出口和服务通道已更新到路线判断。"
		"official_notice":
			official_info_read = true
			begin_alert()
			return "官方警报已确认：进入警报态，目标改为撤离、服务通道或等待援助。"
		"door_lock":
			door_lock_checked = true
			return "门锁检查：合格避险空间应可上锁、避开视线、远离玻璃暴露。"
		"support_phone":
			support_phone_seen = true
			return "蓝灯电话：这是求助和报告渠道，不是冒险探索目标。"
		"clue":
			if not interaction.get("found", false):
				clues_found = min(3, clues_found + 1)
			return "线索已记录：服务通道需要三条线索确认后才能使用。"
	return "交互已记录。"


func can_use_secret_exit(required_clues: int) -> bool:
	return clues_found >= required_clues


func finish(title: String, body: String, ending: String) -> void:
	if phase == PHASE_ALL_CLEAR:
		return
	phase = PHASE_ALL_CLEAR
	ending_type = ending
	outcome_title = title
	outcome_body = body
	finished.emit(title, body)
	phase_changed.emit(phase)


func hud_state(location: String, bottles: int) -> Dictionary:
	return {
		"phase": phase,
		"location": location,
		"bottles": bottles,
		"clues": clues_found,
		"police_eta": police_eta,
		"objective": _objective_text(),
		"mission": _mission_text(),
	}


func _objective_text() -> String:
	if phase == PHASE_OPENING:
		return "跟随导览，熟悉地图板和官方信息。"
	if phase == PHASE_EXPLORE:
		return "完成导览任务，确认警报和安全空间原则。"
	if phase == PHASE_ALERT:
		return "选择低暴露路线：主出口、服务通道或安全等待。"
	return "查看复盘。"


func _mission_text() -> String:
	if phase == PHASE_OPENING:
		return "Enter 开始导览；先读地图板，再确认官方警报。"
	if phase == PHASE_EXPLORE:
		var map_done: String = "✓ 地图板" if map_reads > 0 else "□ 地图板"
		var door_done: String = "✓ 门锁" if door_lock_checked else "□ 门锁"
		var alert_done: String = "✓ 手机警报" if official_info_read else "□ 手机警报"
		return "%s   %s   %s\n导览阶段不会奖励冲出口。" % [map_done, door_done, alert_done]
	if phase == PHASE_ALERT:
		var clue_text: String = "线索 %d/3" % clues_found
		var wait_text: String = "ETA %ds" % int(police_eta)
		return "%s   %s\nA 主出口窗口  B 服务通道  C 合格空间等待" % [clue_text, wait_text]
	return "本局结束，查看复盘。"
