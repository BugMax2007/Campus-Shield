class_name UIRouter
extends CanvasLayer

const MapGuideScript := preload("res://scripts/ui/MapGuide.gd")

const INK := Color8(24, 38, 52)
const MUTED := Color8(88, 103, 113)
const PAPER := Color8(239, 243, 232, 244)
const PAPER_DARK := Color8(210, 224, 216, 244)
const NAVY := Color8(18, 36, 50, 236)
const BLUE := Color8(39, 112, 151)
const TEAL := Color8(42, 139, 151)
const GREEN := Color8(73, 145, 108)
const YELLOW := Color8(236, 181, 58)
const RED := Color8(198, 70, 66)

signal start_requested
signal resume_requested
signal restart_requested
signal menu_requested
signal exit_requested

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
var toast_panel: PanelContainer
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
	opening_panel.visible = true


func show_play() -> void:
	_hide_all()
	hud_panel.visible = true


func show_phone(state: Dictionary) -> void:
	_hide_all()
	hud_panel.visible = true
	phone_panel.visible = true
	phone_timeline_label.text = "08:55  导览开始：确认最近地图板、出口与服务通道位置。\n\n09:02  官方提醒：紧急状态下优先读取学校通知，不传播未确认信息。\n\n09:07  当前建议：如果警报触发，先确认位置，再选择低暴露路线或合格安全空间。"
	phone_side_label.text = "当前目标\n%s\n\n资源\n瓶子 %d   线索 %d/3\n\n警方 ETA\n%ds\n\n原则\n用官方信息校正路线；不要为了探索返回高暴露走廊。" % [
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
	map_route_label.text = "当前位置：%s\n\n主出口：高风险，只有守卫离开视线时可尝试。\n\n服务通道：需要 %d/3 条线索，齐全后低暴露撤离。\n\n等待援助：必须留在合格安全空间，直到警方 ETA 归零。" % [
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
	debrief_body.text = "%s\n\n路径判断\n1. 官方信息优先：手机、广播、地图板比传言可靠。\n2. 空间判断：可锁门、避开玻璃、远离公共走廊的空间更合格。\n3. 路线判断：主出口暴露高，服务通道需要线索确认。\n\n本局记录：线索 %d/3，地图板读取 %d 次。" % [
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
	alert_label.text = "官方警报  确认信息 / 降低暴露 / 选择低风险路线" if phase == "Alert" else "导览状态  熟悉地图板 / 门锁 / 官方警报 / 服务路线"
	interaction_label.text = interaction_text


func toast(message: String) -> void:
	toast_label.text = message
	toast_panel.visible = true
	toast_label.visible = true
	var tween: Tween = create_tween()
	tween.tween_interval(4.0)
	tween.tween_callback(func() -> void:
		toast_label.visible = false
		toast_panel.visible = false
	)


func _hide_all() -> void:
	for child: Node in root.get_children():
		if child is CanvasItem:
			(child as CanvasItem).visible = false


func _build_menu() -> void:
	menu_panel = _panel("MainMenu", Rect2(0.055, 0.08, 0.89, 0.82), PAPER, BLUE)
	var body: HBoxContainer = _content_hbox(menu_panel, "Body", 36)
	var hero: VBoxContainer = _vbox("Hero", 22)
	hero.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(hero)
	hero.add_child(_eyebrow("LIBRARY + STUDENT CENTER"))
	hero.add_child(_label("Campus Shield", 58, INK))
	hero.add_child(_label("叙事型潜行校园安全教育游戏", 28, BLUE))
	hero.add_child(_label("通过游戏体验，学习在潜在紧急情况下如何确认信息、降低暴露并保护自己。", 22, INK))
	hero.add_child(_guide_card("第一关目标", "跟随导览机器人熟悉地图板、手机警报、门锁和服务通道。警报后选择撤离、服务通道或等待援助。", GREEN))
	hero.add_child(_guide_card("表达边界", "危险以视野、封锁、广播和 NPC 行为表达；不展示血腥、武器细节或攻击者视角。", YELLOW))
	var actions: VBoxContainer = _vbox("Actions", 18)
	actions.custom_minimum_size = Vector2(360, 0)
	body.add_child(actions)
	actions.add_child(_label("开始设置", 25, INK))
	actions.add_child(_info_chip("模式  剧情关卡", TEAL))
	actions.add_child(_info_chip("路线  主出口 / 服务通道 / 等待援助", GREEN))
	actions.add_child(_info_chip("操作  WASD / E / Q / M / Tab / Esc", BLUE))
	var start_button: Button = _button("开始游戏 / Start", true)
	start_button.pressed.connect(func() -> void: start_requested.emit())
	actions.add_child(start_button)
	var quit_button: Button = _button("退出游戏 / Quit", false)
	quit_button.pressed.connect(func() -> void: exit_requested.emit())
	actions.add_child(quit_button)
	root.add_child(menu_panel)


func _build_opening() -> void:
	opening_panel = _panel("Opening", Rect2(0.09, 0.12, 0.82, 0.72), PAPER, TEAL)
	var body: VBoxContainer = _content_vbox(opening_panel, "Body", 36, 20)
	body.add_child(_eyebrow("ORIENTATION"))
	body.add_child(_label("开场导览", 46, INK))
	body.add_child(_guide_card("1. 到校导览", "导览机器人先介绍地图板、楼层门牌、教室门锁和可读的出口标识。", BLUE))
	body.add_child(_guide_card("2. 日常任务", "玩家在图书馆和学生中心之间熟悉路线，并收集服务通道线索。", GREEN))
	body.add_child(_guide_card("3. 警报突发", "进入警报态后，通过手机、广播和地图终端确认信息，再决定转移或等待。", RED))
	body.add_child(_label("按 Enter 开始关卡。", 24, BLUE))
	root.add_child(opening_panel)


func _build_hud() -> void:
	hud_panel = Control.new()
	hud_panel.name = "HUD"
	hud_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	alert_label = _hud_chip("AlertStrip", Rect2(0.18, 0.025, 0.64, 0.062), NAVY, YELLOW, 18)
	location_label = _hud_chip("LocationChip", Rect2(0.018, 0.105, 0.29, 0.060), NAVY, TEAL, 16)
	objective_label = _hud_chip("ObjectiveChip", Rect2(0.325, 0.105, 0.36, 0.060), NAVY, GREEN, 16)
	status_label = _hud_chip("StatusChip", Rect2(0.715, 0.105, 0.267, 0.060), NAVY, YELLOW, 16)
	interaction_label = _hud_chip("ActionBar", Rect2(0.28, 0.905, 0.44, 0.068), Color8(20, 43, 57, 238), TEAL, 17)
	toast_label = _hud_chip("ToastTray", Rect2(0.018, 0.785, 0.47, 0.092), Color8(22, 43, 54, 232), YELLOW, 15)
	toast_panel = _chip_panel(toast_label)
	toast_panel.visible = false
	root.add_child(hud_panel)


func _build_phone() -> void:
	phone_panel = _panel("Phone", Rect2(0.18, 0.07, 0.64, 0.86), PAPER, TEAL)
	var body: VBoxContainer = _content_vbox(phone_panel, "Body", 30, 16)
	body.add_child(_modal_header("手机信息终端", "Official Phone / Tab 或 Esc 关闭"))
	var columns: HBoxContainer = _hbox("PhoneColumns", 22)
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(columns)
	var timeline: PanelContainer = _card_box("官方通知时间线", BLUE)
	timeline.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var timeline_body: VBoxContainer = _card_body(timeline)
	phone_timeline_label = _label("", 18, INK)
	phone_timeline_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	timeline_body.add_child(phone_timeline_label)
	columns.add_child(timeline)
	var side: PanelContainer = _card_box("当前判断", GREEN)
	side.custom_minimum_size = Vector2(300, 0)
	var side_body: VBoxContainer = _card_body(side)
	phone_side_label = _label("", 18, INK)
	phone_side_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	side_body.add_child(phone_side_label)
	columns.add_child(side)
	root.add_child(phone_panel)


func _build_map() -> void:
	map_panel = _panel("MapTerminal", Rect2(0.04, 0.055, 0.92, 0.86), PAPER, BLUE)
	var body: VBoxContainer = _content_vbox(map_panel, "Body", 28, 16)
	body.add_child(_modal_header("楼层导览牌", "Floor Guide / 只可在地图板附近打开"))
	var columns: HBoxContainer = _hbox("MapColumns", 22)
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(columns)
	map_guide = MapGuideScript.new()
	map_guide.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_guide.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_guide.custom_minimum_size = Vector2(680, 430)
	columns.add_child(map_guide)
	var side: PanelContainer = _card_box("路线状态", YELLOW)
	side.custom_minimum_size = Vector2(350, 0)
	var side_body: VBoxContainer = _card_body(side)
	map_route_label = _label("", 18, INK)
	map_route_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	side_body.add_child(map_route_label)
	side_body.add_child(_info_chip("图例  绿=合格避险空间  黄=出口/导视  红=高暴露区域", YELLOW))
	side_body.add_child(_label("Esc / Enter 关闭地图终端", 16, MUTED))
	columns.add_child(side)
	root.add_child(map_panel)


func _build_pause() -> void:
	pause_panel = _panel("Pause", Rect2(0.24, 0.18, 0.52, 0.62), PAPER, YELLOW)
	var body: HBoxContainer = _content_hbox(pause_panel, "Body", 34)
	var actions: VBoxContainer = _vbox("Actions", 16)
	actions.custom_minimum_size = Vector2(300, 0)
	body.add_child(actions)
	actions.add_child(_eyebrow("PAUSED"))
	actions.add_child(_label("暂停", 40, INK))
	var resume_button: Button = _button("继续游戏 / Resume", true)
	resume_button.pressed.connect(func() -> void: resume_requested.emit())
	actions.add_child(resume_button)
	var menu_button: Button = _button("返回主菜单 / Main Menu", false)
	menu_button.pressed.connect(func() -> void: menu_requested.emit())
	actions.add_child(menu_button)
	var quit_button: Button = _button("退出游戏 / Quit", false)
	quit_button.pressed.connect(func() -> void: exit_requested.emit())
	actions.add_child(quit_button)
	var help: PanelContainer = _card_box("快捷键", BLUE)
	help.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_card_body(help).add_child(_label("Esc 继续\nM 仅在地图板附近打开导览\nTab 打开手机\nQ 抛瓶子制造噪声窗口\nE 与地图板、门锁、线索互动", 18, INK))
	body.add_child(help)
	root.add_child(pause_panel)


func _build_debrief() -> void:
	debrief_panel = _panel("Debrief", Rect2(0.08, 0.09, 0.84, 0.78), PAPER, GREEN)
	var body: VBoxContainer = _content_vbox(debrief_panel, "Body", 34, 18)
	body.add_child(_eyebrow("DEBRIEF"))
	debrief_title = _label("", 40, INK)
	body.add_child(debrief_title)
	debrief_body = _label("", 19, INK)
	debrief_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(debrief_body)
	var actions: HBoxContainer = _hbox("DebriefActions", 18)
	var restart_button: Button = _button("重新开始 / Restart", true)
	restart_button.pressed.connect(func() -> void: restart_requested.emit())
	actions.add_child(restart_button)
	var menu_button: Button = _button("返回主菜单 / Main Menu", false)
	menu_button.pressed.connect(func() -> void: menu_requested.emit())
	actions.add_child(menu_button)
	body.add_child(actions)
	root.add_child(debrief_panel)


func _panel(panel_name: String, anchors: Rect2, fill: Color, border: Color) -> PanelContainer:
	var panel: PanelContainer = PanelContainer.new()
	panel.name = panel_name
	panel.anchor_left = anchors.position.x
	panel.anchor_top = anchors.position.y
	panel.anchor_right = anchors.position.x + anchors.size.x
	panel.anchor_bottom = anchors.position.y + anchors.size.y
	panel.offset_left = 0
	panel.offset_top = 0
	panel.offset_right = 0
	panel.offset_bottom = 0
	panel.visible = false
	panel.add_theme_stylebox_override("panel", _style_box(fill, border, 20, 2))
	return panel


func _content_vbox(panel: PanelContainer, node_name: String, margin: int, separation: int) -> VBoxContainer:
	var margin_node: MarginContainer = _margin_container(margin)
	var box: VBoxContainer = _vbox(node_name, separation)
	margin_node.add_child(box)
	panel.add_child(margin_node)
	return box


func _content_hbox(panel: PanelContainer, node_name: String, margin: int) -> HBoxContainer:
	var margin_node: MarginContainer = _margin_container(margin)
	var box: HBoxContainer = _hbox(node_name, 28)
	margin_node.add_child(box)
	panel.add_child(margin_node)
	return box


func _margin_container(margin: int) -> MarginContainer:
	var margin_node: MarginContainer = MarginContainer.new()
	margin_node.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin_node.offset_left = margin
	margin_node.offset_top = margin
	margin_node.offset_right = -margin
	margin_node.offset_bottom = -margin
	return margin_node


func _vbox(node_name: String, separation: int = 18) -> VBoxContainer:
	var box: VBoxContainer = VBoxContainer.new()
	box.name = node_name
	box.add_theme_constant_override("separation", separation)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return box


func _hbox(node_name: String, separation: int = 24) -> HBoxContainer:
	var box: HBoxContainer = HBoxContainer.new()
	box.name = node_name
	box.add_theme_constant_override("separation", separation)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return box


func _card_box(title: String, accent: Color) -> PanelContainer:
	var panel: PanelContainer = PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _style_box(Color8(255, 255, 247, 218), accent, 16, 2))
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var margin_node: MarginContainer = _margin_container(18)
	margin_node.name = "Margin"
	var box: VBoxContainer = _vbox("CardBody", 12)
	box.add_child(_label(title, 20, accent))
	margin_node.add_child(box)
	panel.add_child(margin_node)
	return panel


func _card_body(card: PanelContainer) -> VBoxContainer:
	return card.get_node("Margin/CardBody") as VBoxContainer


func _guide_card(title: String, body: String, accent: Color) -> PanelContainer:
	var card: PanelContainer = PanelContainer.new()
	card.add_theme_stylebox_override("panel", _style_box(Color8(255, 255, 247, 214), accent, 16, 1))
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var margin_node: MarginContainer = _margin_container(16)
	var box: VBoxContainer = _vbox("GuideCard", 8)
	box.add_child(_label(title, 20, accent))
	box.add_child(_label(body, 17, INK))
	margin_node.add_child(box)
	card.add_child(margin_node)
	return card


func _modal_header(title: String, hint: String) -> HBoxContainer:
	var header: HBoxContainer = _hbox("ModalHeader", 18)
	var title_label: Label = _label(title, 30, INK)
	title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title_label)
	header.add_child(_label(hint, 16, MUTED))
	return header


func _info_chip(text: String, accent: Color) -> Label:
	var label: Label = _label(text, 16, accent)
	label.add_theme_constant_override("outline_size", 1)
	label.add_theme_color_override("font_outline_color", Color8(255, 255, 247))
	return label


func _eyebrow(text: String) -> Label:
	var label: Label = _label(text, 15, TEAL)
	label.add_theme_constant_override("outline_size", 1)
	label.add_theme_color_override("font_outline_color", Color8(255, 255, 247))
	return label


func _button(text: String, primary: bool) -> Button:
	var button: Button = Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(300, 58)
	button.focus_mode = Control.FOCUS_ALL
	button.add_theme_font_size_override("font_size", 19)
	var fill: Color = BLUE if primary else Color8(245, 247, 239)
	var border: Color = BLUE if primary else TEAL
	var font: Color = Color8(248, 247, 238) if primary else INK
	button.add_theme_stylebox_override("normal", _style_box(fill, border, 14, 2))
	button.add_theme_stylebox_override("hover", _style_box(fill.lightened(0.08), border, 14, 2))
	button.add_theme_stylebox_override("pressed", _style_box(fill.darkened(0.08), border, 14, 2))
	button.add_theme_stylebox_override("focus", _style_box(Color8(250, 232, 152, 190), YELLOW, 14, 3))
	button.add_theme_color_override("font_color", font)
	button.add_theme_color_override("font_hover_color", font)
	button.add_theme_color_override("font_pressed_color", font)
	return button


func _label(text: String, size: int, color: Color = INK) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.clip_text = true
	return label


func _hud_chip(node_name: String, anchors: Rect2, fill: Color, accent: Color, font_size: int) -> Label:
	var panel: PanelContainer = _panel(node_name, anchors, fill, accent)
	panel.visible = true
	panel.add_theme_stylebox_override("panel", _style_box(fill, accent, 14, 2))
	var margin_node: MarginContainer = _margin_container(10)
	var label: Label = _label("", font_size, Color8(248, 247, 238))
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	label.add_theme_constant_override("outline_size", 1)
	label.add_theme_color_override("font_outline_color", Color8(0, 0, 0, 120))
	margin_node.add_child(label)
	panel.add_child(margin_node)
	hud_panel.add_child(panel)
	return label


func _chip_panel(label: Label) -> PanelContainer:
	return label.get_parent().get_parent() as PanelContainer


func _style_box(fill: Color, border: Color, radius: int = 16, border_width: int = 2) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = border
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(radius)
	style.shadow_color = Color8(0, 0, 0, 54)
	style.shadow_size = 10
	style.shadow_offset = Vector2(0, 3)
	return style
