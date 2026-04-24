extends Node2D

const LevelLoaderScript := preload("res://scripts/LevelLoader.gd")
const ScenarioStateScript := preload("res://scripts/ScenarioState.gd")
const LevelScript := preload("res://scripts/entities/Level.gd")
const PlayerScript := preload("res://scripts/entities/Player.gd")
const RaiderScript := preload("res://scripts/entities/Raider.gd")
const RobotScript := preload("res://scripts/entities/Robot.gd")
const InteractableScript := preload("res://scripts/entities/Interactable.gd")
const UIRouterScript := preload("res://scripts/ui/UIRouter.gd")

const LEVEL_PATH := "res://data/levels/chapter_01.json"
const MODE_MENU := "menu"
const MODE_OPENING := "opening"
const MODE_PLAY := "play"
const MODE_PHONE := "phone"
const MODE_MAP := "map"
const MODE_PAUSE := "pause"
const MODE_DEBRIEF := "debrief"

var mode: String = MODE_MENU
var loader
var level_data: Dictionary
var level
var player
var scenario
var ui
var interactables: Array = []
var raiders: Array = []
var robots: Array = []
var noises: Array[Dictionary] = []
var camera: Camera2D

func _ready() -> void:
	DisplayServer.window_set_title("Campus Shield")
	loader = LevelLoaderScript.new()
	level_data = loader.load_level(LEVEL_PATH)
	scenario = ScenarioStateScript.new()
	add_child(scenario)
	scenario.toast_requested.connect(_on_toast)
	scenario.finished.connect(_on_finished)
	_build_world()
	_build_ui()
	set_process(true)
	set_process_unhandled_input(true)


func _build_world() -> void:
	level = LevelScript.new()
	level.setup(level_data)
	add_child(level)
	player = PlayerScript.new()
	player.setup(level, level.spawn_position("player_start"))
	player.noise_created.connect(_add_noise)
	add_child(player)
	for item_data: Dictionary in level_data.get("interactables", []):
		var item = InteractableScript.new()
		item.setup(item_data)
		interactables.append(item)
		add_child(item)
	for actor: Dictionary in level_data.get("actors", []):
		var kind: String = str(actor.get("kind", ""))
		if kind == "raider":
			var patrol_id: String = str(actor.get("patrol_id", ""))
			var path: Dictionary = level_data.get("patrol_paths", {}).get(patrol_id, {})
			var raider = RaiderScript.new()
			raider.setup(actor, path, level)
			raider.player_seen.connect(_on_player_seen)
			raider.player_caught.connect(_on_player_caught)
			raiders.append(raider)
			add_child(raider)
		elif kind == "robot":
			var robot = RobotScript.new()
			robot.setup(actor)
			robot.hint_requested.connect(_on_toast)
			robot.noise_created.connect(_add_noise)
			robots.append(robot)
			add_child(robot)
	camera = Camera2D.new()
	camera.enabled = true
	add_child(camera)


func _build_ui() -> void:
	ui = UIRouterScript.new()
	add_child(ui)
	ui.start_requested.connect(_start_game)
	ui.resume_requested.connect(_resume_play)
	ui.restart_requested.connect(_start_game)
	ui.menu_requested.connect(_return_to_menu)
	ui.exit_requested.connect(_quit_game)
	ui.show_menu()


func _start_game() -> void:
	mode = MODE_OPENING
	scenario.reset()
	player.setup(level, level.spawn_position("player_start"))
	player.enabled = false
	noises.clear()
	_reset_actors()
	ui.show_opening()
	ui.update_hud(_hud_state(), "Enter 开始导览")


func _begin_play() -> void:
	mode = MODE_PLAY
	player.enabled = true
	scenario.begin_explore()
	ui.show_play()


func _return_to_menu() -> void:
	mode = MODE_MENU
	player.enabled = false
	ui.show_menu()


func _quit_game() -> void:
	get_tree().quit()


func _resume_play() -> void:
	mode = MODE_PLAY
	player.enabled = true
	ui.show_play()


func _reset_actors() -> void:
	for node in raiders:
		node.queue_free()
	raiders.clear()
	for actor: Dictionary in level_data.get("actors", []):
		if str(actor.get("kind", "")) == "raider":
			var patrol_id: String = str(actor.get("patrol_id", ""))
			var path: Dictionary = level_data.get("patrol_paths", {}).get(patrol_id, {})
			var raider = RaiderScript.new()
			raider.setup(actor, path, level)
			raider.player_seen.connect(_on_player_seen)
			raider.player_caught.connect(_on_player_caught)
			raiders.append(raider)
			add_child(raider)


func _process(delta: float) -> void:
	if mode == MODE_PLAY:
		_update_play(delta)
	_update_camera()


func _update_play(delta: float) -> void:
	player.tick(delta)
	_update_noises(delta)
	scenario.tick(delta, level.is_safe_point(player.position))
	for raider in raiders:
		raider.tick(delta, player.position, scenario.phase, noises)
	for robot in robots:
		robot.tick(delta, player.position, scenario.phase)
	_check_exits()
	_update_objective_markers()
	ui.update_hud(_hud_state(), _interaction_prompt())


func _update_camera() -> void:
	if camera == null:
		return
	var viewport_size: Vector2 = get_viewport_rect().size
	var min_pos: Vector2 = viewport_size * 0.5
	var max_pos: Vector2 = level.world_size - viewport_size * 0.5
	camera.position = player.position.clamp(min_pos, max_pos)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if mode == MODE_MENU and event.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
			_start_game()
		elif mode == MODE_OPENING and event.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
			_begin_play()
		elif mode == MODE_DEBRIEF and event.keycode == KEY_R:
			_start_game()
		elif event.is_action_pressed("pause_game"):
			_handle_pause_key()
		elif mode == MODE_PLAY:
			if event.is_action_pressed("interact"):
				_interact()
			elif event.is_action_pressed("throw_item"):
				_throw_bottle()
			elif event.is_action_pressed("open_map"):
				_open_map_if_allowed()
			elif event.is_action_pressed("open_phone"):
				mode = MODE_PHONE
				player.enabled = false
				ui.show_phone(_hud_state())
		elif mode in [MODE_PHONE, MODE_MAP, MODE_PAUSE] and event.keycode in [KEY_ESCAPE, KEY_ENTER, KEY_KP_ENTER, KEY_TAB, KEY_M]:
			_resume_play()


func _handle_pause_key() -> void:
	if mode == MODE_PLAY:
		mode = MODE_PAUSE
		player.enabled = false
		ui.show_pause()
	elif mode in [MODE_PHONE, MODE_MAP, MODE_PAUSE]:
		_resume_play()


func _interact() -> void:
	var nearest = _nearest_interactable()
	if nearest == null:
		_on_toast("附近没有可交互对象。寻找地图板、手机警报、门锁或线索。")
		return
	var item_type: String = nearest.interaction_type()
	if item_type == "map_board":
		scenario.record_interaction(nearest.data)
		mode = MODE_MAP
		player.enabled = false
		ui.show_map(level_data, player.position, _hud_state())
		return
	var message: String = scenario.record_interaction(nearest.data)
	if item_type == "clue":
		nearest.mark_found()
		nearest.data["found"] = true
	_on_toast(message)
	_update_objective_markers()


func _throw_bottle() -> void:
	if player.throw_bottle():
		scenario.record_bottle_throw()
		_on_toast("瓶子已抛出：附近巡逻会短暂调查声音。")
	else:
		_on_toast("没有瓶子了。")


func _open_map_if_allowed() -> void:
	var nearest = _nearest_interactable("map_board")
	if nearest == null:
		_on_toast("地图只能在场景内地图板附近查看。")
		return
	scenario.record_interaction(nearest.data)
	mode = MODE_MAP
	player.enabled = false
	ui.show_map(level_data, player.position, _hud_state())


func _nearest_interactable(type_filter: String = ""):
	var nearest = null
	var best_distance: float = 999999.0
	for item in interactables:
		if item.found and item.interaction_type() == "clue":
			continue
		if type_filter != "" and item.interaction_type() != type_filter:
			continue
		var distance: float = item.position.distance_to(player.position)
		if distance < best_distance and item.is_near(player.position):
			best_distance = distance
			nearest = item
	return nearest


func _interaction_prompt() -> String:
	var item = _nearest_interactable()
	if item == null:
		return "E 交互   Q 抛瓶子   Tab 手机   M 地图板   Esc 暂停"
	return "E 交互：%s" % item.label()


func _check_exits() -> void:
	var exit_data: Dictionary = level.exit_at(player.position)
	if exit_data.is_empty():
		return
	if scenario.phase not in [ScenarioStateScript.PHASE_ALERT, ScenarioStateScript.PHASE_ROUTE]:
		_on_toast("导览阶段不能撤离：先确认官方警报和路线信息。")
		return
	var exit_type: String = str(exit_data.get("type", ""))
	if exit_type == "main":
		if _main_exit_guarded():
			_on_toast("主出口被守卫覆盖。需要等待窗口、制造噪声或选择其他路线。")
			return
		scenario.finish("主出口撤离 / Main Exit", "你利用窗口到达北门出口，但这条路线暴露度最高。", "main_exit")
	elif exit_type == "secret":
		var required: int = int(exit_data.get("required_clues", 3))
		if not scenario.can_use_secret_exit(required):
			_on_toast("服务通道未确认：需要三条线索后才能使用。")
			return
		scenario.finish("服务通道撤离 / Service Route", "你通过线索确认了低暴露服务路线，并避开主出口风险。", "secret_exit")


func _update_objective_markers() -> void:
	var target_types: Array[String] = []
	if scenario.phase == ScenarioStateScript.PHASE_EXPLORE:
		if scenario.map_reads <= 0:
			target_types = ["map_board"]
		elif not scenario.door_lock_checked:
			target_types = ["door_lock"]
		elif not scenario.official_info_read:
			target_types = ["official_notice"]
	elif scenario.phase in [ScenarioStateScript.PHASE_ALERT, ScenarioStateScript.PHASE_ROUTE] and scenario.clues_found < 3:
		target_types = ["clue"]
	elif scenario.phase in [ScenarioStateScript.PHASE_ALERT, ScenarioStateScript.PHASE_ROUTE]:
		target_types = ["route_sign"]
	for item in interactables:
		var should_highlight: bool = target_types.has(item.interaction_type())
		if item.interaction_type() == "clue" and item.found:
			should_highlight = false
		item.set_highlighted(should_highlight)
	var active_exits: Array[String] = []
	if scenario.phase in [ScenarioStateScript.PHASE_ALERT, ScenarioStateScript.PHASE_ROUTE]:
		active_exits.append("main")
		if scenario.clues_found >= 3:
			active_exits.append("secret")
	level.set_active_exit_types(active_exits)


func _main_exit_guarded() -> bool:
	for raider in raiders:
		if raider.role == "guard" and raider.position.distance_to(player.position) < 260.0:
			if raider.state in ["Distracted", "InvestigateNoise", "Search", "Return"]:
				return false
			return not level.line_blocked(raider.position, player.position)
	return false


func _update_noises(delta: float) -> void:
	for index: int in range(noises.size() - 1, -1, -1):
		noises[index]["timer"] = float(noises[index].get("timer", 0.0)) - delta
		if float(noises[index].get("timer", 0.0)) <= 0.0:
			noises.remove_at(index)


func _add_noise(noise_position: Vector2) -> void:
	noises.append({"position": noise_position, "timer": 4.5})


func _on_player_seen(_raider_id: String) -> void:
	scenario.record_exposure()
	_on_toast("你被发现了：立刻打断视线，利用书架或房间遮挡。")
	for raider in raiders:
		if raider.actor_id != _raider_id:
			raider.force_investigate(player.position)


func _on_player_caught(_raider_id: String) -> void:
	scenario.finish("搜索区内被发现 / Caught", "你在高暴露区域停留太久，巡逻到达了你的位置。", "caught")


func _on_finished(title: String, body: String) -> void:
	mode = MODE_DEBRIEF
	player.enabled = false
	ui.show_debrief(title, scenario.build_debrief(title, body), _hud_state())


func _on_toast(message: String) -> void:
	ui.toast(message)


func _hud_state() -> Dictionary:
	var state: Dictionary = scenario.hud_state(level.room_name_at(player.position), player.bottles)
	state["map_reads"] = scenario.map_reads
	return state
