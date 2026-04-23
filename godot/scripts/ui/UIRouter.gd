class_name UIRouter
extends CanvasLayer

const MapGuideScript := preload("res://scripts/ui/MapGuide.gd")

const INK := Color8(23, 33, 40)
const MUTED := Color8(76, 87, 94)
const PAPER := Color8(246, 248, 240, 246)
const GLASS := Color8(246, 248, 240, 220)
const NAVY := Color8(16, 34, 46, 238)
const BLUE := Color8(36, 113, 150)
const TEAL := Color8(36, 148, 157)
const GREEN := Color8(70, 146, 101)
const YELLOW := Color8(235, 178, 52)
const RED := Color8(199, 67, 61)
const WHITE := Color8(250, 250, 244)

signal start_requested
signal resume_requested
signal restart_requested
signal menu_requested
signal exit_requested

var root: Control
var menu_panel: Panel
var opening_panel: Panel
var hud_panel: Control
var phone_panel: Panel
var map_panel: Panel
var pause_panel: Panel
var debrief_panel: Panel
var mission_panel: Panel
var toast_panel: Panel
var alert_panel: Panel
var location_label: Label
var objective_label: Label
var mission_label: Label
var status_label: Label
var alert_label: Label
var interaction_label: Label
var toast_label: Label
var phone_timeline_label: Label
var phone_side_label: Label
var map_route_label: Label
var debrief_title: Label
var debrief_body: Label
var map_guide

func _ready() -> void:
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)
	_build_menu()
	_build_opening()
	_build_hud()
	_build_phone()
	_build_map()
	_build_pause()
	_build_debrief()
	show_menu()


func show_menu() -> void:
	_hide_all()
	menu_panel.visible = true


func show_opening() -> void:
	_hide_all()
	hud_panel.visible = true
	opening_panel.visible = true
	_set_hud_dimmed(true)


func show_play() -> void:
	_hide_all()
	hud_panel.visible = true
	_set_hud_dimmed(false)


func show_phone(state: Dictionary) -> void:
	_hide_all()
	hud_panel.visible = true
	phone_panel.visible = true
	phone_timeline_label.text = "08:55  导览开始：确认地图板、出口、门锁和服务通道。\n\n09:02  官方提醒：紧急状态以学校通知和应急部门信息为准。\n\n09:07  当前建议：不要盲走，先确认位置，再选择低暴露路线。"
	phone_side_label.text = "目标\n%s\n\n资源\n瓶子 %d   线索 %d/3\n\n警方 ETA\n%ds\n\n最近原则\n官方信息 > 现场传言；低暴露路线 > 好奇探索。" % [
		state.get("objective", ""),
		int(state.get("bottles", 0)),
		int(state.get("clues", 0)),
		int(state.get("police_eta", 0)),
	]


func show_map(level_data: Dictionary, player_position: Vector2, state: Dictionary) -> void:
	_hide_all()
	hud_panel.visible = true
	map_panel.visible = true
	map_guide.update_map(level_data, player_position)
	map_route_label.text = "当前位置\n%s\n\n主出口\n高风险。守卫离开视线或被噪声引开后才有窗口。\n\n服务通道\n需要 %d/3 条线索。齐全后可低暴露撤离。\n\n等待援助\n进入合格安全空间，保持低暴露直到 ETA 归零。" % [
		state.get("location", ""),
		int(state.get("clues", 0)),
	]


func show_pause() -> void:
	_hide_all()
	hud_panel.visible = true
	pause_panel.visible = true


func show_debrief(title: String, body: String, state: Dictionary) -> void:
	_hide_all()
	debrief_panel.visible = true
	debrief_title.text = title
	debrief_body.text = "%s\n\n复盘\n1. 是否先确认官方信息。\n2. 是否利用地图板判断路线，而不是在走廊里试错。\n3. 是否使用书架、房间和门锁降低暴露。\n4. 是否把主出口、服务通道、等待援助三条路线区分清楚。\n\n记录：线索 %d/3，地图板读取 %d 次。" % [
		body,
		int(state.get("clues", 0)),
		int(state.get("map_reads", 0)),
	]


func update_hud(state: Dictionary, interaction_text: String) -> void:
	var phase: String = str(state.get("phase", "Explore"))
	location_label.text = str(state.get("location", ""))
	objective_label.text = str(state.get("objective", ""))
	mission_label.text = str(state.get("mission", ""))
	status_label.text = "瓶子 %d  线索 %d/3  ETA %ds" % [
		int(state.get("bottles", 0)),
		int(state.get("clues", 0)),
		int(state.get("police_eta", 0)),
	]
	alert_label.text = "官方警报：确认信息，避开高暴露区域" if phase == "Alert" else "导览：熟悉地图板、门锁、手机警报"
	alert_panel.add_theme_stylebox_override("panel", _style_box(RED if phase == "Alert" else NAVY, YELLOW, 8, 2))
	interaction_label.text = interaction_text


func toast(message: String) -> void:
	toast_label.text = message
	toast_panel.visible = true
	var tween: Tween = create_tween()
	tween.tween_interval(4.0)
	tween.tween_callback(func() -> void: toast_panel.visible = false)


func _hide_all() -> void:
	for child: Node in root.get_children():
		if child is CanvasItem:
			(child as CanvasItem).visible = false


func _build_menu() -> void:
	menu_panel = _panel("MainMenu", Rect2(0.06, 0.08, 0.88, 0.82), PAPER, BLUE, 8)
	_add_label(menu_panel, "Campus Shield", Rect2(0.06, 0.08, 0.56, 0.14), 54, INK)
	_add_label(menu_panel, "图书馆 + 学生中心 / 潜行教育关卡", Rect2(0.06, 0.22, 0.58, 0.06), 24, BLUE)
	_add_label(menu_panel, "通过游戏体验，学习在潜在紧急情况下如何确认信息、降低暴露并保护自己。", Rect2(0.06, 0.31, 0.58, 0.12), 22, INK)
	_add_sign(menu_panel, Rect2(0.06, 0.50, 0.26, 0.12), "主出口", "高风险撤离窗口", RED)
	_add_sign(menu_panel, Rect2(0.35, 0.50, 0.26, 0.12), "服务通道", "收集 3 条线索", GREEN)
	_add_sign(menu_panel, Rect2(0.06, 0.66, 0.55, 0.10), "等待援助", "进入合格安全空间，坚持到 ETA 归零", YELLOW)
	_add_label(menu_panel, "WASD 移动  E 交互  Q 抛瓶子  M 地图板  Tab 手机  Esc 暂停", Rect2(0.06, 0.82, 0.58, 0.06), 17, MUTED)
	_add_label(menu_panel, "开始", Rect2(0.70, 0.18, 0.20, 0.05), 28, INK)
	var start_button: Button = _button(menu_panel, "开始游戏", Rect2(0.68, 0.30, 0.24, 0.11), true)
	start_button.pressed.connect(func() -> void: start_requested.emit())
	var quit_button: Button = _button(menu_panel, "退出", Rect2(0.68, 0.45, 0.24, 0.09), false)
	quit_button.pressed.connect(func() -> void: exit_requested.emit())
	_add_label(menu_panel, "第一关目标清晰：读地图、确认警报、找线索、避开巡逻、完成三种结局之一。", Rect2(0.68, 0.63, 0.24, 0.18), 18, MUTED)
	root.add_child(menu_panel)


func _build_opening() -> void:
	opening_panel = _panel("Opening", Rect2(0.13, 0.70, 0.74, 0.22), Color8(246, 248, 240, 235), TEAL, 8)
	_add_label(opening_panel, "导览任务", Rect2(0.035, 0.12, 0.16, 0.16), 25, INK)
	_add_label(opening_panel, "1. 读最近地图板  2. 查官方手机警报  3. 记住服务通道线索位置", Rect2(0.23, 0.13, 0.64, 0.13), 20, INK)
	_add_label(opening_panel, "按 Enter 开始。警报后不要盲目冲出口，先确认路线。", Rect2(0.23, 0.52, 0.64, 0.13), 18, MUTED)
	root.add_child(opening_panel)


func _build_hud() -> void:
	hud_panel = Control.new()
	hud_panel.name = "HUD"
	hud_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(hud_panel)
	alert_panel = _hud_panel("AlertStrip", Rect2(0.30, 0.020, 0.40, 0.060), NAVY, YELLOW)
	alert_label = _label(alert_panel, "", Rect2(0.04, 0.18, 0.92, 0.60), 17, WHITE)
	var location_panel: Panel = _hud_panel("LocationChip", Rect2(0.020, 0.035, 0.25, 0.075), NAVY, TEAL)
	_add_label(location_panel, "位置", Rect2(0.04, 0.08, 0.25, 0.30), 13, Color8(201, 231, 230))
	location_label = _label(location_panel, "", Rect2(0.04, 0.40, 0.92, 0.48), 15, WHITE)
	var objective_panel: Panel = _hud_panel("ObjectiveChip", Rect2(0.020, 0.125, 0.32, 0.100), Color8(21, 48, 54, 235), GREEN)
	_add_label(objective_panel, "当前目标", Rect2(0.035, 0.08, 0.30, 0.26), 13, Color8(206, 236, 215))
	objective_label = _label(objective_panel, "", Rect2(0.035, 0.40, 0.92, 0.48), 15, WHITE)
	mission_panel = _hud_panel("MissionPanel", Rect2(0.020, 0.245, 0.32, 0.135), Color8(244, 248, 240, 226), GREEN)
	_add_label(mission_panel, "任务清单", Rect2(0.035, 0.08, 0.30, 0.22), 13, GREEN)
	mission_label = _label(mission_panel, "", Rect2(0.035, 0.33, 0.92, 0.58), 14, INK)
	var status_panel: Panel = _hud_panel("StatusChip", Rect2(0.735, 0.035, 0.245, 0.075), NAVY, YELLOW)
	status_label = _label(status_panel, "", Rect2(0.055, 0.25, 0.90, 0.50), 16, WHITE)
	var action_panel: Panel = _hud_panel("ActionBar", Rect2(0.30, 0.905, 0.40, 0.065), Color8(20, 43, 57, 238), TEAL)
	interaction_label = _label(action_panel, "", Rect2(0.04, 0.20, 0.92, 0.58), 16, WHITE)
	toast_panel = _hud_panel("ToastTray", Rect2(0.020, 0.815, 0.42, 0.080), Color8(22, 43, 54, 236), YELLOW)
	toast_label = _label(toast_panel, "", Rect2(0.04, 0.18, 0.92, 0.62), 15, WHITE)
	toast_panel.visible = false


func _build_phone() -> void:
	phone_panel = _panel("Phone", Rect2(0.18, 0.08, 0.64, 0.82), PAPER, TEAL, 8)
	_add_label(phone_panel, "手机信息终端", Rect2(0.04, 0.05, 0.40, 0.06), 30, INK)
	_add_label(phone_panel, "Tab / Esc 关闭", Rect2(0.72, 0.065, 0.20, 0.04), 15, MUTED)
	var left: Panel = _child_panel(phone_panel, "PhoneTimeline", Rect2(0.04, 0.17, 0.54, 0.74), Color8(255, 255, 247, 230), BLUE)
	_add_label(left, "官方通知时间线", Rect2(0.04, 0.04, 0.45, 0.07), 20, BLUE)
	phone_timeline_label = _label(left, "", Rect2(0.04, 0.16, 0.90, 0.76), 18, INK)
	var right: Panel = _child_panel(phone_panel, "PhoneStatus", Rect2(0.62, 0.17, 0.34, 0.74), Color8(255, 255, 247, 230), GREEN)
	_add_label(right, "当前判断", Rect2(0.06, 0.04, 0.45, 0.07), 20, GREEN)
	phone_side_label = _label(right, "", Rect2(0.06, 0.16, 0.88, 0.76), 18, INK)
	root.add_child(phone_panel)


func _build_map() -> void:
	map_panel = _panel("MapTerminal", Rect2(0.04, 0.06, 0.92, 0.84), PAPER, BLUE, 8)
	_add_label(map_panel, "楼层导览牌", Rect2(0.035, 0.045, 0.32, 0.06), 30, INK)
	_add_label(map_panel, "只可在场景地图板附近打开", Rect2(0.61, 0.060, 0.28, 0.04), 15, MUTED)
	map_guide = MapGuideScript.new()
	map_guide.anchor_left = 0.035
	map_guide.anchor_top = 0.15
	map_guide.anchor_right = 0.68
	map_guide.anchor_bottom = 0.93
	map_guide.offset_left = 0
	map_guide.offset_top = 0
	map_guide.offset_right = 0
	map_guide.offset_bottom = 0
	map_panel.add_child(map_guide)
	var side: Panel = _child_panel(map_panel, "MapRoute", Rect2(0.71, 0.15, 0.25, 0.78), Color8(255, 255, 247, 230), YELLOW)
	_add_label(side, "路线状态", Rect2(0.06, 0.04, 0.70, 0.07), 21, INK)
	map_route_label = _label(side, "", Rect2(0.06, 0.16, 0.88, 0.72), 17, INK)
	root.add_child(map_panel)


func _build_pause() -> void:
	pause_panel = _panel("Pause", Rect2(0.30, 0.20, 0.40, 0.55), PAPER, YELLOW, 8)
	_add_label(pause_panel, "暂停", Rect2(0.08, 0.08, 0.40, 0.09), 36, INK)
	var resume_button: Button = _button(pause_panel, "继续游戏", Rect2(0.08, 0.25, 0.36, 0.13), true)
	resume_button.pressed.connect(func() -> void: resume_requested.emit())
	var menu_button: Button = _button(pause_panel, "返回主菜单", Rect2(0.08, 0.43, 0.36, 0.12), false)
	menu_button.pressed.connect(func() -> void: menu_requested.emit())
	var quit_button: Button = _button(pause_panel, "退出游戏", Rect2(0.08, 0.60, 0.36, 0.12), false)
	quit_button.pressed.connect(func() -> void: exit_requested.emit())
	_add_label(pause_panel, "M 近地图板打开导览\nTab 手机\nQ 抛瓶子制造噪声窗口\nE 与线索、门锁、地图板互动", Rect2(0.52, 0.25, 0.38, 0.45), 17, MUTED)
	root.add_child(pause_panel)


func _build_debrief() -> void:
	debrief_panel = _panel("Debrief", Rect2(0.10, 0.10, 0.80, 0.76), PAPER, GREEN, 8)
	_add_label(debrief_panel, "复盘", Rect2(0.05, 0.05, 0.22, 0.07), 30, GREEN)
	debrief_title = _label(debrief_panel, "", Rect2(0.05, 0.15, 0.65, 0.08), 34, INK)
	debrief_body = _label(debrief_panel, "", Rect2(0.05, 0.27, 0.64, 0.55), 19, INK)
	var restart_button: Button = _button(debrief_panel, "重新开始", Rect2(0.73, 0.28, 0.20, 0.10), true)
	restart_button.pressed.connect(func() -> void: restart_requested.emit())
	var menu_button: Button = _button(debrief_panel, "主菜单", Rect2(0.73, 0.43, 0.20, 0.10), false)
	menu_button.pressed.connect(func() -> void: menu_requested.emit())
	root.add_child(debrief_panel)


func _panel(panel_name: String, anchors: Rect2, fill: Color, border: Color, radius: int) -> Panel:
	var panel: Panel = Panel.new()
	panel.name = panel_name
	_anchor(panel, anchors)
	panel.visible = false
	panel.add_theme_stylebox_override("panel", _style_box(fill, border, radius, 2))
	return panel


func _child_panel(parent: Control, panel_name: String, anchors: Rect2, fill: Color, border: Color) -> Panel:
	var panel: Panel = _panel(panel_name, anchors, fill, border, 8)
	panel.visible = true
	parent.add_child(panel)
	return panel


func _hud_panel(panel_name: String, anchors: Rect2, fill: Color, border: Color) -> Panel:
	var panel: Panel = _panel(panel_name, anchors, fill, border, 8)
	panel.visible = true
	hud_panel.add_child(panel)
	return panel


func _add_sign(parent: Control, anchors: Rect2, title: String, body: String, accent: Color) -> void:
	var sign: Panel = _child_panel(parent, "%sSign" % title, anchors, Color8(255, 255, 247, 222), accent)
	_add_label(sign, title, Rect2(0.06, 0.10, 0.85, 0.34), 20, accent)
	_add_label(sign, body, Rect2(0.06, 0.52, 0.88, 0.30), 15, INK)


func _button(parent: Control, text: String, anchors: Rect2, primary: bool) -> Button:
	var button: Button = Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_ALL
	_anchor(button, anchors)
	button.add_theme_font_size_override("font_size", 19)
	var fill: Color = BLUE if primary else WHITE
	var border: Color = BLUE if primary else TEAL
	var font: Color = WHITE if primary else INK
	button.add_theme_stylebox_override("normal", _style_box(fill, border, 8, 2))
	button.add_theme_stylebox_override("hover", _style_box(fill.lightened(0.08), border, 8, 2))
	button.add_theme_stylebox_override("pressed", _style_box(fill.darkened(0.08), border, 8, 2))
	button.add_theme_stylebox_override("focus", _style_box(Color8(250, 232, 152, 215), YELLOW, 8, 3))
	button.add_theme_color_override("font_color", font)
	button.add_theme_color_override("font_hover_color", font)
	button.add_theme_color_override("font_pressed_color", font)
	parent.add_child(button)
	return button


func _add_label(parent: Control, text: String, anchors: Rect2, size: int, color: Color) -> Label:
	var label: Label = _label(parent, text, anchors, size, color)
	return label


func _label(parent: Control, text: String, anchors: Rect2, size: int, color: Color) -> Label:
	var label: Label = Label.new()
	label.text = text
	_anchor(label, anchors)
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.clip_text = true
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	parent.add_child(label)
	return label


func _anchor(control: Control, anchors: Rect2) -> void:
	control.anchor_left = anchors.position.x
	control.anchor_top = anchors.position.y
	control.anchor_right = anchors.position.x + anchors.size.x
	control.anchor_bottom = anchors.position.y + anchors.size.y
	control.offset_left = 0
	control.offset_top = 0
	control.offset_right = 0
	control.offset_bottom = 0


func _set_hud_dimmed(dimmed: bool) -> void:
	var alpha: float = 0.55 if dimmed else 1.0
	for child: Node in hud_panel.get_children():
		if child is CanvasItem:
			(child as CanvasItem).modulate.a = alpha
	if toast_panel != null:
		toast_panel.modulate.a = 1.0


func _style_box(fill: Color, border: Color, radius: int = 8, border_width: int = 2) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = border
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(radius)
	style.shadow_color = Color8(0, 0, 0, 48)
	style.shadow_size = 8
	style.shadow_offset = Vector2(0, 3)
	return style
