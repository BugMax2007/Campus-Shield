class_name ScenarioState
extends Node

signal toast_requested(message: String)
signal finished(title: String, body: String)
signal phase_changed(phase: String)

const PHASE_INTRO := "IntroGuide"
const PHASE_EXPLORE := "ExploreChecklist"
const PHASE_ALERT := "AlertActive"
const PHASE_ROUTE := "RouteCommit"
const PHASE_ENDING := "Ending"
const PHASE_DEBRIEF := "Debrief"

const SAFE_WAIT_SECONDS := 75.0

var phase: String = PHASE_INTRO
var elapsed: float = 0.0
var alert_elapsed: float = 0.0
var alert_delay: float = 70.0
var assistance_delay: float = 210.0
var police_eta: float = 210.0
var clues_found: int = 0
var map_reads: int = 0
var official_info_read: bool = false
var door_lock_checked: bool = false
var support_phone_seen: bool = false
var safe_wait_time: float = 0.0
var exposures: int = 0
var bottle_throws: int = 0
var route_commitment: String = ""
var ending_type: String = ""
var outcome_title: String = ""
var outcome_body: String = ""
var inventory: Dictionary = {}
var npc_outcomes: Dictionary = {}
var misinfo_checked: bool = false
var slow_walk_time: float = 0.0
var hide_uses: int = 0
var floor_changes: int = 0
var service_control_ready: bool = false
var found_interactions: Dictionary = {}
var debrief_events: Array[String] = []

func reset() -> void:
	phase = PHASE_INTRO
	elapsed = 0.0
	alert_elapsed = 0.0
	police_eta = assistance_delay
	clues_found = 0
	map_reads = 0
	official_info_read = false
	door_lock_checked = false
	support_phone_seen = false
	safe_wait_time = 0.0
	exposures = 0
	bottle_throws = 0
	route_commitment = ""
	ending_type = ""
	outcome_title = ""
	outcome_body = ""
	inventory.clear()
	npc_outcomes.clear()
	misinfo_checked = false
	slow_walk_time = 0.0
	hide_uses = 0
	floor_changes = 0
	service_control_ready = false
	found_interactions.clear()
	debrief_events.clear()
	phase_changed.emit(phase)


func begin_explore() -> void:
	phase = PHASE_EXPLORE
	debrief_events.append("你先进入导览阶段，目标是确认地图、门锁和官方警报。")
	toast_requested.emit("导览开始：先读地图板，再检查门锁，最后确认官方警报。")
	phase_changed.emit(phase)


func tick(delta: float, player_in_safe_room: bool) -> void:
	if phase == PHASE_EXPLORE:
		elapsed += delta
		if elapsed >= alert_delay or official_info_read:
			begin_alert()
	elif phase in [PHASE_ALERT, PHASE_ROUTE]:
		alert_elapsed += delta
		police_eta = max(0.0, assistance_delay - alert_elapsed)
		if player_in_safe_room and door_lock_checked:
			safe_wait_time += delta
		else:
			safe_wait_time = max(0.0, safe_wait_time - delta * 0.75)
		if safe_wait_time >= SAFE_WAIT_SECONDS and police_eta <= assistance_delay - SAFE_WAIT_SECONDS:
			finish("等待援助成功 / Assistance Arrived", "你留在可上锁、低暴露的合格空间中，没有为了好奇返回走廊。", "wait_assistance")


func begin_alert() -> void:
	if phase in [PHASE_ALERT, PHASE_ROUTE, PHASE_ENDING, PHASE_DEBRIEF]:
		return
	phase = PHASE_ALERT
	if not official_info_read:
		debrief_events.append("警报自动触发前，你还没有主动确认官方信息。")
	toast_requested.emit("官方警报触发：确认位置，避开高暴露走廊，选择一条路线。")
	phase_changed.emit(phase)


func record_interaction(interaction: Dictionary) -> String:
	var interaction_id: String = str(interaction.get("id", ""))
	var interaction_type: String = str(interaction.get("type", ""))
	var effect_type: String = str(interaction.get("effect_type", interaction_type))
	var required_phase: String = str(interaction.get("required_phase", "any"))
	var requires_item: String = str(interaction.get("requires_item", ""))
	if requires_item != "" and not inventory.has(requires_item):
		return "缺少必要物品：%s。先寻找对应的门禁卡或线索。" % _item_label(requires_item)
	if not _phase_allowed(required_phase):
		return "现在不是使用这个信息的时机。先完成当前目标。"
	if interaction_id != "" and bool(interaction.get("once", true)) and found_interactions.has(interaction_id):
		return "这条信息已经记录过了。查看手机或地图板确认下一步。"
	if interaction_id != "":
		found_interactions[interaction_id] = true
	match effect_type:
		"unlock_map":
			map_reads += 1
			debrief_events.append("你读取地图板，确认了当前位置、出口和服务通道方向。")
			return "地图板已读取：当前位置、主出口、服务通道和安全房间已更新。"
		"trigger_alert":
			official_info_read = true
			debrief_events.append("你通过官方手机警报确认了事件，而不是依赖传言。")
			begin_alert()
			return "官方警报已确认：进入警报态，选择低暴露路线。"
		"validate_safe_room":
			door_lock_checked = true
			debrief_events.append("你检查了门锁，理解合格避险空间需要可上锁、遮挡视线、远离玻璃。")
			return "门锁检查完成：这个原则会影响等待援助结局。"
		"support_info":
			support_phone_seen = true
			debrief_events.append("你识别了蓝灯电话，它是求助渠道，不是冒险路线。")
			return "蓝灯电话已记录：用于求助和报告，不等于安全出口。"
		"service_clue":
			if not interaction.get("found", false):
				clues_found = min(3, clues_found + 1)
				debrief_events.append("你找到服务通道线索 %d/3。" % clues_found)
			return "服务通道线索 %d/3：三条线索齐全后可使用低暴露路线。" % clues_found
		"grant_item":
			var item_id: String = str(interaction.get("grants_item", ""))
			if item_id != "":
				inventory[item_id] = true
			debrief_events.append("你获得了门禁物品：%s。" % _item_label(item_id))
			return "获得：%s。它可以打开对应门禁或服务控制点。" % _item_label(item_id)
		"service_control":
			service_control_ready = true
			debrief_events.append("你启动了服务门控制箱，服务通道路线具备可执行条件。")
			return "服务门控制箱已启动：线索齐全并持有门禁卡后可走服务通道。"
		"npc_lost_student":
			npc_outcomes["lost_student"] = "helped"
			map_reads += 1
			debrief_events.append("你用地图板帮助迷路学生确认位置，没有带对方穿过高风险走廊。")
			return "迷路学生已结伴确认地图：这属于低风险协助。"
		"npc_misinfo":
			npc_outcomes["misinfo_student"] = "corrected"
			misinfo_checked = true
			official_info_read = true
			debrief_events.append("你纠正了错误传言，选择以官方警报为准。")
			begin_alert()
			return "错误信息已纠正：以官方警报和现场导视为准。"
		"npc_staff_clue":
			npc_outcomes["staff"] = "service_hint"
			clues_found = min(3, clues_found + 1)
			debrief_events.append("图书馆员工提供了服务通道线索。")
			return "员工提示已记录：服务通道线索 %d/3。" % clues_found
		"hide_spot":
			hide_uses += 1
			debrief_events.append("你短暂躲藏以打断视线。")
			return "你进入临时躲藏点：只能短时使用，不能替代合格安全空间。"
		"commit_main_exit":
			route_commitment = "main"
			phase = PHASE_ROUTE
			return "路线已倾向主出口：高风险，需要避开守卫视线或制造噪声窗口。"
		"commit_service_route":
			route_commitment = "service"
			phase = PHASE_ROUTE
			return "路线已倾向服务通道：低暴露，但必须集齐三条线索。"
	return "信息已记录：查看当前目标选择下一步。"


func can_use_secret_exit(required_clues: int) -> bool:
	return clues_found >= required_clues and inventory.has("service_keycard") and service_control_ready


func record_bottle_throw() -> void:
	bottle_throws += 1
	debrief_events.append("你使用瓶子制造噪声窗口。")


func record_slow_walk(delta: float) -> void:
	slow_walk_time += delta


func record_floor_change(floor_id: String) -> void:
	floor_changes += 1
	debrief_events.append("你切换到 %s，使用楼层信息重新判断路线。" % floor_id)


func record_exposure() -> void:
	exposures += 1
	if exposures == 1:
		toast_requested.emit("你被发现了：打断视线，进入遮挡或房间。")


func finish(title: String, body: String, ending: String) -> void:
	if phase in [PHASE_ENDING, PHASE_DEBRIEF]:
		return
	phase = PHASE_ENDING
	ending_type = ending
	outcome_title = title
	outcome_body = body
	finished.emit(title, body)
	phase_changed.emit(phase)


func build_debrief(title: String, body: String) -> String:
	var route_text: String = "路线选择：%s" % _route_text()
	var info_text: String = "官方信息：%s" % ("已确认" if official_info_read else "未主动确认")
	var safe_text: String = "安全空间：%s" % ("检查过门锁" if door_lock_checked else "未检查门锁")
	var pressure_text: String = "暴露记录：被发现 %d 次，瓶子使用 %d 次。" % [exposures, bottle_throws]
	var npc_text: String = "NPC 协助：迷路学生 %s，错误信息 %s，员工线索 %s。" % [
		"已协助" if npc_outcomes.has("lost_student") else "未处理",
		"已纠正" if misinfo_checked else "未纠正",
		"已获得" if npc_outcomes.has("staff") else "未获得",
	]
	var stealth_text: String = "潜行行为：慢走 %.0fs，躲藏 %d 次，楼层切换 %d 次。" % [slow_walk_time, hide_uses, floor_changes]
	var advice: Array[String] = [
		"先确认官方信息，再行动；不要根据传言或好奇心移动。",
		"路线选择要看暴露度：主出口不一定最安全，服务通道需要证据确认。",
		"合格避险空间应可上锁、避开视线、远离玻璃和公共走廊。",
	]
	var event_text: String = "\n".join(debrief_events.slice(max(0, debrief_events.size() - 5), debrief_events.size()))
	return "%s\n\n%s\n%s\n%s\n%s\n%s\n%s\n\n关键记录\n%s\n\n复盘建议\n1. %s\n2. %s\n3. %s\n\n说明：本游戏是教育体验，不能替代学校、当地政府或应急部门的真实指令。" % [
		body,
		route_text,
		info_text,
		safe_text,
		pressure_text,
		npc_text,
		stealth_text,
		event_text,
		advice[0],
		advice[1],
		advice[2],
	]


func hud_state(location: String, bottles: int) -> Dictionary:
	var inventory_labels: PackedStringArray = PackedStringArray()
	for item_id: String in inventory.keys():
		inventory_labels.append(_item_label(item_id))
	return {
		"phase": phase,
		"location": location,
		"bottles": bottles,
		"clues": clues_found,
		"police_eta": police_eta,
		"safe_wait": safe_wait_time,
		"exposures": exposures,
		"inventory": "、".join(inventory_labels),
		"npc_count": npc_outcomes.size(),
		"floor_changes": floor_changes,
		"objective": _objective_text(),
		"mission": _mission_text(),
	}


func _phase_allowed(required_phase: String) -> bool:
	if required_phase == "any" or required_phase == "":
		return true
	if required_phase == "pre_alert":
		return phase in [PHASE_INTRO, PHASE_EXPLORE]
	if required_phase == "alert":
		return phase in [PHASE_ALERT, PHASE_ROUTE]
	return required_phase == phase


func _objective_text() -> String:
	if phase == PHASE_INTRO:
		return "进入导览：先理解地图和官方信息来源。"
	if phase == PHASE_EXPLORE:
		return "导览清单：地图板、门锁、手机警报。"
	if phase == PHASE_ALERT:
		return "警报中：选择主出口、服务通道或安全等待。"
	if phase == PHASE_ROUTE:
		return "执行路线：降低暴露，不要回到公共走廊试错。"
	return "查看复盘。"


func _mission_text() -> String:
	if phase == PHASE_EXPLORE:
		return "%s   %s   %s" % [
			"✓ 地图板" if map_reads > 0 else "□ 地图板",
			"✓ 门锁" if door_lock_checked else "□ 门锁",
			"✓ 手机警报" if official_info_read else "□ 手机警报",
		]
	if phase in [PHASE_ALERT, PHASE_ROUTE]:
		return "线索 %d/3   卡 %s   控制 %s   ETA %ds" % [
			clues_found,
			"有" if inventory.has("service_keycard") else "无",
			"开" if service_control_ready else "关",
			int(police_eta),
		]
	return "Enter 开始导览"


func _route_text() -> String:
	match ending_type:
		"main_exit":
			return "主出口撤离，高风险但成功避开守卫窗口"
		"secret_exit":
			return "服务通道撤离，依靠线索、门禁卡和服务控制确认低暴露路线"
		"wait_assistance":
			return "安全等待，留在合格空间直到援助到达"
		"caught":
			return "失败，被巡逻持续发现或追上"
	return "未完成"


func _item_label(item_id: String) -> String:
	if item_id == "service_keycard":
		return "服务门禁卡"
	return item_id
