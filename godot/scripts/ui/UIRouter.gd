class_name UIRouter
extends CanvasLayer

const MapGuideScript := preload("res://scripts/ui/MapGuide.gd")

signal start_requested
signal resume_requested
signal restart_requested
signal menu_requested

var root: Control
var menu_panel: PanelContainer
var opening_panel: PanelContainer
var hud_panel: Control
var phone_panel: PanelContainer
var map_panel: PanelContainer
var pause_panel: PanelContainer
var debrief_panel: PanelContainer
var toast_label: Label
var location_label: Label
var objective_label: Label
var status_label: Label
var alert_label: Label
var interaction_label: Label
var phone_body: Label
var debrief_title: Label
var debrief_body: Label
var map_guide: Control

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
	opening_panel.visible = true


func show_play() -> void:
	_hide_all()
	hud_panel.visible = true


func show_phone(state: Dictionary) -> void:
	hud_panel.visible = true
	phone_panel.visible = true
	phone_body.text = "官方信息：确认学校警报和应急部门指令。\n\n当前目标：%s\n\n线索：%d/3\n瓶子：%d\n警方 ETA：%ds\n\n原则：降低暴露，不为好奇心返回高风险区域。" % [
		state.get("objective", ""),
		int(state.get("clues", 0)),
		int(state.get("bottles", 0)),
		int(state.get("police_eta", 0)),
	]


func show_map(level_data: Dictionary, player_position: Vector2, state: Dictionary) -> void:
	hud_panel.visible = true
	map_panel.visible = true
	map_guide.update_map(level_data, player_position)
	var route_text: String = "主出口：高风险，可能被守卫覆盖。\n服务通道：需要 %d/3 条线索。\n等待援助：必须留在合格安全空间。" % int(state.get("clues", 0))
	var route_label: Label = map_panel.get_node("Body/RouteText") as Label
	route_label.text = route_text


func show_pause() -> void:
	hud_panel.visible = true
	pause_panel.visible = true


func show_debrief(title: String, body: String, state: Dictionary) -> void:
	_hide_all()
	debrief_panel.visible = true
	debrief_title.text = title
	debrief_body.text = "%s\n\n复盘重点：\n- 是否优先使用官方信息？\n- 是否降低走廊和玻璃暴露？\n- 是否通过地图板确认路线，而不是盲走？\n\n本局线索：%d/3  地图读取：%d" % [
		body,
		int(state.get("clues", 0)),
		int(state.get("map_reads", 0)),
	]


func update_hud(state: Dictionary, interaction_text: String) -> void:
	location_label.text = "位置  %s" % str(state.get("location", ""))
	objective_label.text = "目标  %s" % str(state.get("objective", ""))
	status_label.text = "瓶子 %d   线索 %d/3   ETA %ds" % [
		int(state.get("bottles", 0)),
		int(state.get("clues", 0)),
		int(state.get("police_eta", 0)),
	]
	var phase: String = str(state.get("phase", "Explore"))
	alert_label.text = "官方警报：确认信息、降低暴露、选择低风险路线" if phase == "Alert" else "导览：熟悉地图板、门锁、官方警报和服务路线"
	interaction_label.text = interaction_text


func toast(message: String) -> void:
	toast_label.text = message
	toast_label.visible = true
	var tween: Tween = create_tween()
	tween.tween_interval(4.0)
	tween.tween_callback(func() -> void: toast_label.visible = false)


func _hide_all() -> void:
	for child: Node in root.get_children():
		if child is CanvasItem:
			(child as CanvasItem).visible = false


func _build_menu() -> void:
	menu_panel = _panel("MainMenu", Rect2(80, 70, 1120, 580))
	var body: HBoxContainer = _hbox("Body")
	menu_panel.add_child(body)
	var hero: VBoxContainer = _vbox("Hero")
	hero.custom_minimum_size = Vector2(660, 0)
	body.add_child(hero)
	hero.add_child(_label("Campus Shield", 54))
	hero.add_child(_label("叙事型潜行校园安全教育游戏", 26))
	hero.add_child(_label("通过游戏体验，学习在潜在紧急情况下如何确认信息、降低暴露并保护自己。", 20))
	var actions: VBoxContainer = _vbox("Actions")
	body.add_child(actions)
	var start_button: Button = Button.new()
	start_button.text = "Start / 开始"
	start_button.custom_minimum_size = Vector2(320, 72)
	start_button.pressed.connect(func() -> void: start_requested.emit())
	actions.add_child(start_button)
	actions.add_child(_label("WASD 移动  E 交互  Q 抛瓶子  M 地图板  Tab 手机  Esc 暂停", 16))
	root.add_child(menu_panel)


func _build_opening() -> void:
	opening_panel = _panel("Opening", Rect2(110, 90, 1060, 540))
	var body: VBoxContainer = _vbox("Body")
	opening_panel.add_child(body)
	body.add_child(_label("开场导览 / Orientation", 42))
	body.add_child(_label("导览机器人会先介绍地图板、教室门锁、官方警报和服务通道线索。", 24))
	body.add_child(_label("警报后，你需要通过手机、广播和地图终端确认信息，再决定撤离、转移或等待援助。", 22))
	body.add_child(_label("按 Enter 进入关卡。", 24))
	root.add_child(opening_panel)


func _build_hud() -> void:
	hud_panel = Control.new()
	hud_panel.name = "HUD"
	hud_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	alert_label = _floating_label(Rect2(28, 18, 1224, 44), 18)
	location_label = _floating_label(Rect2(28, 76, 390, 42), 16)
	objective_label = _floating_label(Rect2(430, 76, 520, 42), 16)
	status_label = _floating_label(Rect2(964, 76, 288, 42), 16)
	interaction_label = _floating_label(Rect2(360, 648, 560, 42), 16)
	toast_label = _floating_label(Rect2(28, 584, 700, 46), 15)
	toast_label.visible = false
	hud_panel.add_child(alert_label)
	hud_panel.add_child(location_label)
	hud_panel.add_child(objective_label)
	hud_panel.add_child(status_label)
	hud_panel.add_child(interaction_label)
	hud_panel.add_child(toast_label)
	root.add_child(hud_panel)


func _build_phone() -> void:
	phone_panel = _panel("Phone", Rect2(410, 54, 460, 612))
	var body: VBoxContainer = _vbox("Body")
	phone_panel.add_child(body)
	body.add_child(_label("手机 / Official Phone", 32))
	phone_body = _label("", 18)
	phone_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(phone_body)
	body.add_child(_label("Esc / Tab / Enter 关闭", 16))
	root.add_child(phone_panel)


func _build_map() -> void:
	map_panel = _panel("MapTerminal", Rect2(70, 52, 1140, 616))
	var body: HBoxContainer = _hbox("Body")
	map_panel.add_child(body)
	map_guide = MapGuideScript.new()
	map_guide.custom_minimum_size = Vector2(720, 520)
	body.add_child(map_guide)
	var side: VBoxContainer = _vbox("Side")
	body.add_child(side)
	side.add_child(_label("楼层导览 / Floor Guide", 30))
	var route: Label = _label("", 18)
	route.name = "RouteText"
	route.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	side.add_child(route)
	side.add_child(_label("只可在场景地图板附近打开。Esc / Enter 关闭。", 16))
	root.add_child(map_panel)


func _build_pause() -> void:
	pause_panel = _panel("Pause", Rect2(340, 140, 600, 440))
	var body: VBoxContainer = _vbox("Body")
	pause_panel.add_child(body)
	body.add_child(_label("暂停 / Paused", 38))
	var resume_button: Button = Button.new()
	resume_button.text = "继续游戏 / Resume"
	resume_button.custom_minimum_size = Vector2(360, 58)
	resume_button.pressed.connect(func() -> void: resume_requested.emit())
	body.add_child(resume_button)
	var menu_button: Button = Button.new()
	menu_button.text = "返回主菜单 / Main Menu"
	menu_button.custom_minimum_size = Vector2(360, 58)
	menu_button.pressed.connect(func() -> void: menu_requested.emit())
	body.add_child(menu_button)
	body.add_child(_label("Esc 继续；当前版本为 Godot 重构第一关。", 16))
	root.add_child(pause_panel)


func _build_debrief() -> void:
	debrief_panel = _panel("Debrief", Rect2(110, 84, 1060, 552))
	var body: VBoxContainer = _vbox("Body")
	debrief_panel.add_child(body)
	debrief_title = _label("", 38)
	body.add_child(debrief_title)
	debrief_body = _label("", 20)
	debrief_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(debrief_body)
	var restart_button: Button = Button.new()
	restart_button.text = "重新开始 / Restart"
	restart_button.custom_minimum_size = Vector2(300, 58)
	restart_button.pressed.connect(func() -> void: restart_requested.emit())
	body.add_child(restart_button)
	root.add_child(debrief_panel)


func _panel(panel_name: String, rect: Rect2) -> PanelContainer:
	var panel: PanelContainer = PanelContainer.new()
	panel.name = panel_name
	panel.position = rect.position
	panel.size = rect.size
	panel.visible = false
	return panel


func _vbox(node_name: String) -> VBoxContainer:
	var box: VBoxContainer = VBoxContainer.new()
	box.name = node_name
	box.add_theme_constant_override("separation", 18)
	box.set_anchors_preset(Control.PRESET_FULL_RECT)
	box.offset_left = 28
	box.offset_top = 28
	box.offset_right = -28
	box.offset_bottom = -28
	return box


func _hbox(node_name: String) -> HBoxContainer:
	var box: HBoxContainer = HBoxContainer.new()
	box.name = node_name
	box.add_theme_constant_override("separation", 26)
	box.set_anchors_preset(Control.PRESET_FULL_RECT)
	box.offset_left = 28
	box.offset_top = 28
	box.offset_right = -28
	box.offset_bottom = -28
	return box


func _label(text: String, size: int) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return label


func _floating_label(rect: Rect2, size: int) -> Label:
	var label: Label = _label("", size)
	label.position = rect.position
	label.size = rect.size
	label.add_theme_color_override("font_color", Color8(245, 243, 235))
	return label
