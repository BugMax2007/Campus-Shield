extends SceneTree

const UIRouterScript := preload("res://scripts/ui/UIRouter.gd")
const LevelLoaderScript := preload("res://scripts/LevelLoader.gd")

var failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var loader = LevelLoaderScript.new()
	var level_data: Dictionary = loader.load_level("res://data/levels/chapter_01.json")
	for resolution: Vector2i in [Vector2i(1280, 720), Vector2i(1600, 900), Vector2i(1920, 1080)]:
		DisplayServer.window_set_size(resolution)
		get_root().size = resolution
		var ui = UIRouterScript.new()
		get_root().add_child(ui)
		await process_frame
		for screen: String in ["menu", "opening", "gameplay", "alert", "phone", "map", "pause", "debrief"]:
			_show_screen(ui, screen, level_data)
			await process_frame
			_check_visible_controls(ui.root, screen, resolution)
			if screen in ["opening", "gameplay", "alert"]:
				_check_no_blocking_overlay(ui.root, screen, resolution)
			if screen in ["gameplay", "alert"]:
				_check_hud_visible(ui, screen, resolution)
				_check_hud_overlap(ui, screen, resolution)
		ui.queue_free()
		await process_frame
	if failures.is_empty():
		print("UI layout check OK")
		quit()
	for failure: String in failures:
		push_error(failure)
	quit()


func _show_screen(ui, screen: String, level_data: Dictionary) -> void:
	var base_state: Dictionary = {
		"location": "图书馆阅览区 / Library Reading",
		"objective": "确认官方信息并选择低暴露路线",
		"phase": "ExploreChecklist",
		"bottles": 2,
		"clues": 1,
		"police_eta": 315,
		"map_reads": 1,
	}
	match screen:
		"menu":
			ui.show_menu()
		"opening":
			ui.show_opening()
		"gameplay":
			ui.show_play()
			ui.update_hud(base_state, "E 交互：地图板 / Map Board")
		"alert":
			var alert_state: Dictionary = base_state.duplicate()
			alert_state["phase"] = "AlertActive"
			ui.show_play()
			ui.update_hud(alert_state, "Q 抛瓶子制造噪声窗口；Esc 暂停")
		"phone":
			ui.show_phone(base_state)
		"map":
			ui.show_map(level_data, Vector2(650, 1220), base_state)
		"pause":
			ui.show_pause()
		"debrief":
			ui.show_debrief("服务通道撤离", "你通过地图板和线索确认了低暴露路线。", base_state)


func _check_visible_controls(control: Control, screen: String, resolution: Vector2i) -> void:
	if not control.visible:
		return
	var rect: Rect2 = control.get_global_rect()
	if rect.size.x > 1.0 and rect.size.y > 1.0:
		if rect.position.x < -1.0 or rect.position.y < -1.0 or rect.end.x > float(resolution.x) + 1.0 or rect.end.y > float(resolution.y) + 1.0:
			failures.append("%s %s out of bounds at %s: %s" % [screen, control.name, str(resolution), str(rect)])
	for child: Node in control.get_children():
		if child is Control:
			_check_visible_controls(child as Control, screen, resolution)


func _check_hud_overlap(ui, screen: String, resolution: Vector2i) -> void:
	var rects: Array[Dictionary] = []
	for child: Node in ui.hud_panel.get_children():
		if child is Control and (child as Control).visible:
			var rect: Rect2 = (child as Control).get_global_rect()
			if rect.size.x > 1.0 and rect.size.y > 1.0:
				rects.append({"name": child.name, "rect": rect.grow(-3.0)})
	for i: int in range(rects.size()):
		for j: int in range(i + 1, rects.size()):
			if (rects[i]["rect"] as Rect2).intersects(rects[j]["rect"] as Rect2):
				failures.append("%s HUD overlap at %s: %s vs %s" % [screen, str(resolution), rects[i]["name"], rects[j]["name"]])


func _check_hud_visible(ui, screen: String, resolution: Vector2i) -> void:
	var visible_chips: int = 0
	for child: Node in ui.hud_panel.get_children():
		if child is Control and (child as Control).visible:
			visible_chips += 1
	if visible_chips < 4:
		failures.append("%s HUD has only %d visible chips at %s" % [screen, visible_chips, str(resolution)])


func _check_no_blocking_overlay(control: Control, screen: String, resolution: Vector2i) -> void:
	if not control.visible:
		return
	if control is Panel:
		var rect: Rect2 = control.get_global_rect()
		var coverage: float = rect.size.x * rect.size.y / float(resolution.x * resolution.y)
		var limit: float = 0.24 if screen == "opening" else 0.14
		if coverage > limit:
			failures.append("%s has blocking panel %s coverage %.2f at %s" % [screen, control.name, coverage, str(resolution)])
	for child: Node in control.get_children():
		if child is Control:
			_check_no_blocking_overlay(child as Control, screen, resolution)
