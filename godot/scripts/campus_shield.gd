extends Node2D

const VIEW_MENU := "menu"
const VIEW_OPENING := "opening"
const VIEW_PLAY := "play"
const VIEW_MAP := "map"
const VIEW_PHONE := "phone"
const VIEW_PAUSE := "pause"
const VIEW_DEBRIEF := "debrief"

const PHASE_EXPLORE := "Explore"
const PHASE_ALERT := "Alert"
const PHASE_ALL_CLEAR := "AllClear"

const COLOR_BG := Color8(15, 26, 38)
const COLOR_GRASS := Color8(77, 117, 91)
const COLOR_FLOOR := Color8(215, 209, 193)
const COLOR_WALL := Color8(45, 62, 74)
const COLOR_ROOM := Color8(229, 225, 211)
const COLOR_ROOM_SAFE := Color8(205, 230, 213)
const COLOR_ROOM_RISK := Color8(232, 200, 191)
const COLOR_OBSTACLE := Color8(90, 84, 72)
const COLOR_PLAYER := Color8(58, 142, 204)
const COLOR_RAIDER := Color8(166, 68, 70)
const COLOR_ROBOT := Color8(72, 176, 188)
const COLOR_WARNING := Color8(236, 183, 54)
const COLOR_TEXT := Color8(244, 247, 242)
const COLOR_INK := Color8(24, 38, 52)
const COLOR_PANEL := Color8(245, 240, 226)
const COLOR_PANEL_DARK := Color8(28, 44, 59)

var view := VIEW_MENU
var phase := PHASE_EXPLORE
var font: Font
var world_size := Vector2(2600, 1800)
var camera := Vector2.ZERO
var player := Vector2(620, 1180)
var player_radius := 18.0
var player_speed := 260.0
var facing := Vector2.RIGHT
var elapsed := 0.0
var alert_elapsed := 0.0
var police_eta := 420.0
var bottles := 3
var clues := 0
var current_room := "Library Commons"
var nearest_action := ""
var toast := "Press Enter to begin the rebuilt Godot vertical slice."
var toast_timer := 6.0
var outcome_title := ""
var outcome_body := ""

var rooms: Array[Dictionary] = []
var obstacles: Array[Rect2] = []
var boards: Array[Dictionary] = []
var exits: Array[Dictionary] = []
var clues_data: Array[Dictionary] = []
var robots: Array[Dictionary] = []
var raiders: Array[Dictionary] = []
var noises: Array[Dictionary] = []

func _ready() -> void:
	DisplayServer.window_set_title("Campus Shield")
	font = ThemeDB.fallback_font
	_build_level()
	set_process(true)
	set_process_input(true)


func _build_level() -> void:
	rooms = [
		{"id": "library_commons", "name": "Library Commons", "rect": Rect2(360, 930, 680, 420), "safe": true},
		{"id": "library_stacks", "name": "Book Stacks", "rect": Rect2(1080, 860, 560, 470), "safe": true},
		{"id": "student_center", "name": "Student Center", "rect": Rect2(380, 360, 620, 420), "safe": false},
		{"id": "classrooms", "name": "Classroom Wing", "rect": Rect2(1080, 300, 680, 440), "safe": true},
		{"id": "service_hall", "name": "Service Hall", "rect": Rect2(1810, 780, 430, 520), "safe": false},
	]
	obstacles = [
		Rect2(470, 1020, 120, 34), Rect2(470, 1110, 120, 34), Rect2(470, 1200, 120, 34),
		Rect2(650, 1020, 120, 34), Rect2(650, 1110, 120, 34), Rect2(650, 1200, 120, 34),
		Rect2(1190, 950, 70, 300), Rect2(1320, 950, 70, 300), Rect2(1450, 950, 70, 300),
		Rect2(490, 475, 390, 44), Rect2(490, 600, 390, 44),
		Rect2(1180, 410, 180, 46), Rect2(1460, 410, 180, 46), Rect2(1180, 580, 460, 46),
		Rect2(1910, 900, 230, 48), Rect2(1910, 1080, 230, 48),
	]
	boards = [
		{"pos": Vector2(1030, 1130), "label": "Library floor map"},
		{"pos": Vector2(980, 510), "label": "Student Center directory"},
		{"pos": Vector2(1760, 520), "label": "Classroom evacuation board"},
	]
	exits = [
		{"id": "north_gate", "name": "North Gate", "rect": Rect2(1230, 40, 260, 90), "type": "main"},
		{"id": "service_tunnel", "name": "Service Tunnel", "rect": Rect2(2190, 1260, 140, 120), "type": "secret"},
	]
	clues_data = [
		{"pos": Vector2(1510, 645), "text": "Maintenance note: tunnel access needs three clues."},
		{"pos": Vector2(1540, 1030), "text": "Stack shelf marker: service hall connects east."},
		{"pos": Vector2(2100, 820), "text": "Robot log: tunnel door is behind the service hall."},
	]
	robots = [
		{"pos": Vector2(720, 940), "home": Vector2(720, 940), "hint": "Guide robot: use map boards instead of guessing routes."},
		{"pos": Vector2(1680, 760), "home": Vector2(1680, 760), "hint": "Security robot: loud objects can redirect a search briefly."},
	]
	raiders = [
		_make_raider("Gate Guard", Vector2(1360, 170), [Vector2(1260, 170), Vector2(1480, 170), Vector2(1480, 285), Vector2(1260, 285)]),
		_make_raider("Library Searcher", Vector2(1460, 870), [Vector2(1120, 880), Vector2(1600, 880), Vector2(1600, 1280), Vector2(1120, 1280)]),
		_make_raider("Student Center Patrol", Vector2(530, 350), [Vector2(420, 335), Vector2(960, 335), Vector2(960, 760), Vector2(420, 760)]),
		_make_raider("Service Hall Patrol", Vector2(2050, 775), [Vector2(1840, 790), Vector2(2220, 790), Vector2(2220, 1280), Vector2(1840, 1280)]),
	]


func _make_raider(label: String, pos: Vector2, patrol: Array[Vector2]) -> Dictionary:
	return {
		"label": label,
		"pos": pos,
		"patrol": patrol,
		"target": 0,
		"state": "Patrol",
		"search_timer": 0.0,
		"heading": Vector2.RIGHT,
		"last_seen": pos,
		"speed": 135.0,
	}


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("pause_game"):
		if view == VIEW_PLAY:
			view = VIEW_PAUSE
		elif view in [VIEW_MAP, VIEW_PHONE, VIEW_PAUSE]:
			view = VIEW_PLAY
		queue_redraw()
		return

	if event is InputEventKey and event.pressed and not event.echo:
		if view == VIEW_MENU and event.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
			_start_game()
		elif view == VIEW_OPENING and event.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
			view = VIEW_PLAY
		elif view == VIEW_DEBRIEF and event.keycode == KEY_R:
			_start_game()
		elif view == VIEW_PAUSE and event.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
			view = VIEW_PLAY
		elif view == VIEW_PLAY:
			if event.is_action_pressed("open_map"):
				_try_open_map()
			elif event.is_action_pressed("open_phone"):
				view = VIEW_PHONE
			elif event.is_action_pressed("interact"):
				_interact()
			elif event.is_action_pressed("throw_item"):
				_throw_bottle()
		elif view in [VIEW_MAP, VIEW_PHONE] and event.keycode in [KEY_M, KEY_TAB, KEY_ESCAPE, KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
			view = VIEW_PLAY
	queue_redraw()


func _start_game() -> void:
	view = VIEW_OPENING
	phase = PHASE_EXPLORE
	player = Vector2(620, 1180)
	facing = Vector2.RIGHT
	elapsed = 0.0
	alert_elapsed = 0.0
	police_eta = 420.0
	bottles = 3
	clues = 0
	noises.clear()
	_build_level()
	_set_toast("Opening: a guide robot introduces map boards, stair nodes, and official alerts.")


func _process(delta: float) -> void:
	if view == VIEW_PLAY:
		_update_game(delta)
	if toast_timer > 0:
		toast_timer -= delta
	queue_redraw()


func _update_game(delta: float) -> void:
	elapsed += delta
	if phase == PHASE_EXPLORE and elapsed > 14.0:
		phase = PHASE_ALERT
		_set_toast("Official alert received. Use verified information, avoid open corridors, and choose a route.")
	if phase == PHASE_ALERT:
		alert_elapsed += delta
		police_eta = max(0.0, 420.0 - alert_elapsed)
		if police_eta <= 0.0 and _player_in_safe_room():
			_finish("Assistance Arrived", "You stayed in a qualifying safe space and waited for official all-clear guidance.")

	_update_player(delta)
	_update_room()
	_update_noises(delta)
	_update_raiders(delta)
	_update_robots(delta)
	_check_exit_conditions()


func _update_player(delta: float) -> void:
	var input_dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if input_dir.length() > 0:
		facing = input_dir.normalized()
		var move := facing * player_speed * delta
		_move_player_axis(Vector2(move.x, 0))
		_move_player_axis(Vector2(0, move.y))


func _move_player_axis(move: Vector2) -> void:
	var next := player + move
	if _point_blocked(next, player_radius):
		return
	player = next.clamp(Vector2(80, 80), world_size - Vector2(80, 80))


func _point_blocked(point: Vector2, radius: float) -> bool:
	var probe := Rect2(point - Vector2(radius, radius), Vector2(radius * 2.0, radius * 2.0))
	for block in obstacles:
		if probe.intersects(block):
			return true
	return false


func _update_room() -> void:
	current_room = "Outdoor Walkway"
	for room in rooms:
		if room.rect.has_point(player):
			current_room = room.name
			return


func _update_noises(delta: float) -> void:
	for i in range(noises.size() - 1, -1, -1):
		noises[i].timer -= delta
		if noises[i].timer <= 0.0:
			noises.remove_at(i)


func _update_raiders(delta: float) -> void:
	for raider in raiders:
		if _can_see_player(raider):
			raider.state = "Chase"
			raider.last_seen = player
			raider.search_timer = 5.0
			_set_toast("You were seen. Break line of sight and use rooms or noise to redirect the search.")
		elif raider.state == "Chase" and raider.pos.distance_to(player) > 520:
			raider.state = "Search"
			raider.search_timer = 6.0
		elif raider.state == "Search":
			raider.search_timer -= delta
			if raider.search_timer <= 0.0:
				raider.state = "Patrol"

		for noise in noises:
			if raider.pos.distance_to(noise.pos) < 360 and raider.state != "Chase":
				raider.state = "InvestigateNoise"
				raider.last_seen = noise.pos
				raider.search_timer = 3.5

		var target := _raider_target(raider)
		_move_raider_toward(raider, target, delta)
		if raider.pos.distance_to(player) < 28:
			_finish("Caught In Search Zone", "The hostile actor reached your position. The safer play is to avoid exposure and break line of sight earlier.")


func _raider_target(raider: Dictionary) -> Vector2:
	if raider.state in ["Chase", "Search", "InvestigateNoise"]:
		return raider.last_seen
	var patrol: Array = raider.patrol
	if patrol.is_empty():
		return raider.pos
	var target: Vector2 = patrol[raider.target]
	if raider.pos.distance_to(target) < 18:
		raider.target = (raider.target + 1) % patrol.size()
		target = patrol[raider.target]
	return target


func _move_raider_toward(raider: Dictionary, target: Vector2, delta: float) -> void:
	var dir: Vector2 = target - raider.pos
	if dir.length() < 1.0:
		return
	var step: Vector2 = dir.normalized() * float(raider.speed) * delta
	var next: Vector2 = raider.pos + step
	if not _point_blocked(next, 16):
		raider.pos = next
		raider.heading = dir.normalized()
	else:
		var sidestep: Vector2 = Vector2(-dir.y, dir.x).normalized() * float(raider.speed) * delta
		if not _point_blocked(raider.pos + sidestep, 16):
			raider.pos += sidestep


func _can_see_player(raider: Dictionary) -> bool:
	if phase != PHASE_ALERT:
		return false
	var to_player: Vector2 = player - raider.pos
	if to_player.length() > 340:
		return false
	var heading: Vector2 = raider.heading
	if heading.length() <= 0.1:
		heading = Vector2.RIGHT
	var angle: float = abs(rad_to_deg(heading.normalized().angle_to(to_player.normalized())))
	if angle > 38:
		return false
	return not _line_blocked(raider.pos, player)


func _line_blocked(start: Vector2, end: Vector2) -> bool:
	for block in obstacles:
		if _segment_intersects_rect(start, end, block):
			return true
	return false


func _segment_intersects_rect(a: Vector2, b: Vector2, rect: Rect2) -> bool:
	var steps: int = max(4, int(a.distance_to(b) / 18.0))
	for i in range(steps + 1):
		var p := a.lerp(b, float(i) / float(steps))
		if rect.has_point(p):
			return true
	return false


func _update_robots(delta: float) -> void:
	for robot in robots:
		var offset := Vector2(cos(elapsed * 0.9), sin(elapsed * 0.7)) * 28.0
		robot.pos = robot.home + offset
		if robot.pos.distance_to(player) < 95 and phase == PHASE_ALERT:
			_set_toast(robot.hint)


func _check_exit_conditions() -> void:
	for exit_data in exits:
		if exit_data.rect.has_point(player):
			if exit_data.type == "main":
				var guard_near := false
				for raider in raiders:
					if raider.label == "Gate Guard" and raider.pos.distance_to(player) < 230:
						guard_near = true
				if guard_near:
					_set_toast("North Gate is covered. Use noise or a different route before attempting evacuation.")
				else:
					_finish("North Gate Evacuation", "You reached the main exit during a safe timing window.")
			elif exit_data.type == "secret":
				if clues >= 3:
					_finish("Service Tunnel Exit", "You found enough evidence to unlock the lower-exposure service route.")
				else:
					_set_toast("Service tunnel locked. Find all three route clues before using it.")


func _player_in_safe_room() -> bool:
	for room in rooms:
		if room.rect.has_point(player):
			return room.safe
	return false


func _try_open_map() -> void:
	if _nearest_board_distance() <= 110:
		view = VIEW_MAP
	else:
		_set_toast("Find a wall-mounted map board to view the floor guide.")


func _nearest_board_distance() -> float:
	var dist := INF
	for board in boards:
		dist = min(dist, player.distance_to(board.pos))
	return dist


func _interact() -> void:
	for board in boards:
		if player.distance_to(board.pos) < 110:
			view = VIEW_MAP
			return
	for clue in clues_data:
		if player.distance_to(clue.pos) < 70 and not clue.get("found", false):
			clue.found = true
			clues += 1
			_set_toast("Clue collected: " + clue.text)
			return
	for robot in robots:
		if player.distance_to(robot.pos) < 90:
			_set_toast(robot.hint)
			return
	_set_toast("No direct interaction here. Check signage, rooms, or official updates.")


func _throw_bottle() -> void:
	if bottles <= 0:
		_set_toast("No bottles left.")
		return
	bottles -= 1
	var pos := player + facing.normalized() * 190.0
	noises.append({"pos": pos, "timer": 4.0})
	_set_toast("Bottle thrown. Nearby searchers may investigate the sound.")


func _finish(title: String, body: String) -> void:
	outcome_title = title
	outcome_body = body
	phase = PHASE_ALL_CLEAR
	view = VIEW_DEBRIEF


func _set_toast(text: String) -> void:
	toast = text
	toast_timer = 5.0


func _draw() -> void:
	var size := get_viewport_rect().size
	if view == VIEW_MENU:
		_draw_menu(size)
	elif view == VIEW_OPENING:
		_draw_opening(size)
	else:
		_draw_world(size)
		_draw_hud(size)
		if view == VIEW_MAP:
			_draw_map_terminal(size)
		elif view == VIEW_PHONE:
			_draw_phone(size)
		elif view == VIEW_PAUSE:
			_draw_pause(size)
		elif view == VIEW_DEBRIEF:
			_draw_debrief(size)


func _draw_world(size: Vector2) -> void:
	camera = (player - size * 0.5).clamp(Vector2.ZERO, world_size - size)
	draw_rect(Rect2(-camera, world_size), COLOR_GRASS)
	for room in rooms:
		var color := COLOR_ROOM_SAFE if room.safe else COLOR_ROOM_RISK
		draw_rect(Rect2(room.rect.position - camera, room.rect.size), color)
		draw_rect(Rect2(room.rect.position - camera, room.rect.size), COLOR_WALL, false, 5.0)
		_draw_text(room.name, room.rect.position - camera + Vector2(18, 32), 18, COLOR_INK)
	for block in obstacles:
		draw_rect(Rect2(block.position - camera, block.size), COLOR_OBSTACLE)
	for board in boards:
		_draw_sign(board.pos - camera, "MAP")
	for clue in clues_data:
		if not clue.get("found", false):
			draw_circle(clue.pos - camera, 11, COLOR_WARNING)
	for exit_data in exits:
		draw_rect(Rect2(exit_data.rect.position - camera, exit_data.rect.size), COLOR_WARNING, false, 4.0)
		_draw_text(exit_data.name, exit_data.rect.position - camera + Vector2(12, 34), 16, COLOR_TEXT)
	for noise in noises:
		draw_circle(noise.pos - camera, 38, Color(1.0, 0.8, 0.25, 0.18))
		draw_circle(noise.pos - camera, 8, COLOR_WARNING)
	for robot in robots:
		_draw_robot(robot.pos - camera)
	for raider in raiders:
		_draw_raider(raider)
	_draw_player(player - camera)


func _draw_raider(raider: Dictionary) -> void:
	var pos: Vector2 = raider.pos - camera
	var heading: Vector2 = raider.heading
	if heading.length() <= 0.1:
		heading = Vector2.RIGHT
	var left := heading.rotated(deg_to_rad(-38)).normalized() * 340
	var right := heading.rotated(deg_to_rad(38)).normalized() * 340
	draw_colored_polygon(PackedVector2Array([pos, pos + left, pos + right]), Color(0.9, 0.18, 0.12, 0.12))
	draw_circle(pos, 17, COLOR_RAIDER)
	draw_circle(pos, 17, Color8(95, 35, 38), false, 3.0)
	_draw_text(raider.state, pos + Vector2(-24, -26), 12, COLOR_TEXT)


func _draw_player(pos: Vector2) -> void:
	draw_circle(pos, 18, COLOR_PLAYER)
	var tip := pos + facing.normalized() * 26
	draw_line(pos, tip, COLOR_TEXT, 3.0)


func _draw_robot(pos: Vector2) -> void:
	draw_rect(Rect2(pos - Vector2(15, 15), Vector2(30, 30)), COLOR_ROBOT)
	draw_circle(pos + Vector2(-6, -2), 3, COLOR_TEXT)
	draw_circle(pos + Vector2(6, -2), 3, COLOR_TEXT)


func _draw_sign(pos: Vector2, label: String) -> void:
	draw_rect(Rect2(pos - Vector2(28, 18), Vector2(56, 36)), COLOR_PANEL)
	draw_rect(Rect2(pos - Vector2(28, 18), Vector2(56, 36)), COLOR_WARNING, false, 3.0)
	_draw_text(label, pos + Vector2(-18, 6), 12, COLOR_INK)


func _draw_hud(size: Vector2) -> void:
	var alert_color := COLOR_WARNING if phase == PHASE_ALERT else COLOR_PANEL_DARK
	draw_rect(Rect2(24, 18, size.x - 48, 48), alert_color)
	var headline := "OFFICIAL ALERT: Confirm information, reduce exposure, choose a low-risk route." if phase == PHASE_ALERT else "Orientation: learn map boards, rooms, routes, and official channels."
	_draw_text(headline, Vector2(42, 49), 18, COLOR_TEXT if phase == PHASE_ALERT else COLOR_PANEL)
	draw_rect(Rect2(24, 78, 360, 48), COLOR_PANEL)
	_draw_text("Location: " + current_room, Vector2(42, 109), 18, COLOR_INK)
	draw_rect(Rect2(size.x - 430, 78, 406, 48), COLOR_PANEL)
	_draw_text("Bottles %d  Clues %d/3  Police ETA %ds" % [bottles, clues, int(police_eta)], Vector2(size.x - 410, 109), 16, COLOR_INK)
	draw_rect(Rect2(size.x * 0.5 - 230, size.y - 76, 460, 48), COLOR_PANEL)
	_draw_text("WASD move  E interact  Q throw  Tab phone  M map  Esc pause", Vector2(size.x * 0.5 - 208, size.y - 45), 14, COLOR_INK)
	if toast_timer > 0:
		draw_rect(Rect2(24, size.y - 142, min(size.x * 0.62, 760), 52), COLOR_PANEL_DARK)
		_draw_text(toast, Vector2(42, size.y - 110), 15, COLOR_TEXT)


func _draw_menu(size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, size), COLOR_BG)
	draw_rect(Rect2(60, 70, size.x * 0.52, size.y - 140), Color8(35, 62, 78))
	draw_rect(Rect2(size.x * 0.62, 70, size.x * 0.31, size.y - 140), COLOR_PANEL)
	_draw_text("Campus Shield", Vector2(92, 150), 54, COLOR_TEXT)
	_draw_text("A 2D stealth survival education game rebuild", Vector2(96, 202), 21, COLOR_WARNING)
	_draw_text("Goal: learn what to do in a potential emergency to better protect yourself through play.", Vector2(96, 260), 18, COLOR_TEXT)
	_draw_text("New Godot vertical slice: patrol AI, noise, map boards, phone, endings.", Vector2(96, 304), 17, COLOR_TEXT)
	draw_rect(Rect2(size.x * 0.655, 180, size.x * 0.24, 68), COLOR_WARNING)
	_draw_text("Start Game", Vector2(size.x * 0.705, 224), 27, COLOR_INK)
	_draw_text("Press Enter", Vector2(size.x * 0.705, 282), 18, COLOR_INK)
	_draw_text("Controls", Vector2(size.x * 0.655, 378), 24, COLOR_INK)
	_draw_text("WASD move / E interact / Q throw bottle", Vector2(size.x * 0.655, 420), 16, COLOR_INK)
	_draw_text("M map board / Tab phone / Esc pause", Vector2(size.x * 0.655, 452), 16, COLOR_INK)


func _draw_opening(size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, size), COLOR_BG)
	draw_rect(Rect2(96, 86, size.x - 192, size.y - 172), COLOR_PANEL)
	_draw_text("Opening Sequence", Vector2(140, 160), 42, COLOR_INK)
	_draw_text("A guide robot brings you through the library entry, shows wall map boards, and explains that official alerts override rumors.", Vector2(140, 230), 22, COLOR_INK)
	_draw_text("The prototype starts after this card. Press Enter to continue.", Vector2(140, 330), 22, COLOR_INK)
	_draw_text("Design direction: fewer debug panels, stronger game readability, and actual stealth decisions.", Vector2(140, 430), 19, COLOR_INK)


func _draw_map_terminal(size: Vector2) -> void:
	_draw_modal_backdrop(size)
	var panel := Rect2(88, 70, size.x - 176, size.y - 140)
	draw_rect(panel, COLOR_PANEL)
	_draw_text("Campus Floor Guide", panel.position + Vector2(34, 48), 34, COLOR_INK)
	var map_rect := Rect2(panel.position + Vector2(34, 92), Vector2(panel.size.x * 0.62, panel.size.y - 126))
	draw_rect(map_rect, Color8(224, 230, 218))
	var scale: float = min(map_rect.size.x / world_size.x, map_rect.size.y / world_size.y)
	var offset := map_rect.position + Vector2(18, 18)
	for room in rooms:
		var r := Rect2(offset + room.rect.position * scale, room.rect.size * scale)
		draw_rect(r, COLOR_ROOM_SAFE if room.safe else COLOR_ROOM_RISK)
		draw_rect(r, COLOR_WALL, false, 2.0)
	for exit_data in exits:
		draw_rect(Rect2(offset + exit_data.rect.position * scale, exit_data.rect.size * scale), COLOR_WARNING, false, 2.0)
	draw_circle(offset + player * scale, 7, COLOR_PLAYER)
	_draw_text("You are here", offset + player * scale + Vector2(10, -8), 12, COLOR_INK)
	var side_x := panel.position.x + panel.size.x * 0.69
	_draw_text("Route Status", Vector2(side_x, panel.position.y + 120), 26, COLOR_INK)
	_draw_text("Main gate: high risk, guarded.", Vector2(side_x, panel.position.y + 170), 17, COLOR_INK)
	_draw_text("Service tunnel: requires 3 clues. Current: %d/3" % clues, Vector2(side_x, panel.position.y + 205), 17, COLOR_INK)
	_draw_text("Police assistance: %ds if waiting in a safe room." % int(police_eta), Vector2(side_x, panel.position.y + 240), 17, COLOR_INK)
	_draw_text("Esc / Enter to close", Vector2(side_x, panel.position.y + panel.size.y - 48), 16, COLOR_INK)


func _draw_phone(size: Vector2) -> void:
	_draw_modal_backdrop(size)
	var phone := Rect2(size.x * 0.32, 56, size.x * 0.36, size.y - 112)
	draw_rect(phone, Color8(20, 31, 43))
	draw_rect(phone.grow(-18), COLOR_PANEL)
	_draw_text("Official Phone", phone.position + Vector2(46, 74), 30, COLOR_TEXT)
	_draw_text("Latest alert", phone.position + Vector2(46, 138), 18, COLOR_INK)
	_draw_text("Use official information, avoid exposed corridors, and do not return to unsafe areas for curiosity.", phone.position + Vector2(46, 182), 17, COLOR_INK)
	_draw_text("Inventory", phone.position + Vector2(46, 276), 20, COLOR_INK)
	_draw_text("Bottles: %d   Clues: %d/3" % [bottles, clues], phone.position + Vector2(46, 316), 17, COLOR_INK)
	_draw_text("Esc / Tab / Enter to close", phone.position + Vector2(46, phone.size.y - 54), 15, COLOR_INK)


func _draw_pause(size: Vector2) -> void:
	_draw_modal_backdrop(size)
	var panel := Rect2(size.x * 0.28, 130, size.x * 0.44, size.y - 260)
	draw_rect(panel, COLOR_PANEL)
	_draw_text("Paused", panel.position + Vector2(44, 70), 38, COLOR_INK)
	_draw_text("Enter: resume", panel.position + Vector2(48, 140), 22, COLOR_INK)
	_draw_text("Esc: resume", panel.position + Vector2(48, 184), 22, COLOR_INK)
	_draw_text("This Godot version is a rebuild foundation, not the final map.", panel.position + Vector2(48, 252), 17, COLOR_INK)


func _draw_debrief(size: Vector2) -> void:
	_draw_modal_backdrop(size)
	var panel := Rect2(90, 80, size.x - 180, size.y - 160)
	draw_rect(panel, COLOR_PANEL)
	_draw_text(outcome_title, panel.position + Vector2(44, 74), 42, COLOR_INK)
	_draw_text(outcome_body, panel.position + Vector2(44, 140), 22, COLOR_INK)
	_draw_text("Review", panel.position + Vector2(44, 240), 28, COLOR_INK)
	_draw_text("- Did you rely on official information?", panel.position + Vector2(58, 292), 19, COLOR_INK)
	_draw_text("- Did you reduce exposure instead of exploring?", panel.position + Vector2(58, 330), 19, COLOR_INK)
	_draw_text("- Did you choose a route with clear cover and an exit condition?", panel.position + Vector2(58, 368), 19, COLOR_INK)
	_draw_text("Press R to restart.", panel.position + Vector2(44, panel.size.y - 54), 18, COLOR_INK)


func _draw_modal_backdrop(size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0, 0, 0, 0.55))


func _draw_text(text: String, pos: Vector2, size: int, color: Color) -> void:
	draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)
