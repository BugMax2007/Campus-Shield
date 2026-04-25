extends SceneTree

const LevelLoaderScript := preload("res://scripts/LevelLoader.gd")
const LevelScript := preload("res://scripts/entities/Level.gd")
const RaiderScript := preload("res://scripts/entities/Raider.gd")

var failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var loader = LevelLoaderScript.new()
	var level_data: Dictionary = loader.load_level("res://data/levels/chapter_01.json")
	var level = LevelScript.new()
	level.setup(level_data)
	get_root().add_child(level)
	for actor: Dictionary in level_data.get("actors", []):
		if str(actor.get("kind", "")) != "raider":
			continue
		var patrol_id: String = str(actor.get("patrol_id", ""))
		var path: Dictionary = level_data.get("patrol_paths", {}).get(patrol_id, {})
		var raider = RaiderScript.new()
		raider.setup(actor, path, level)
		level.add_child(raider)
		var start: Vector2 = raider.position
		for index: int in range(120):
			raider.tick(1.0 / 30.0, Vector2(-9000, -9000), "ExploreChecklist", [])
		if raider.position.distance_to(start) < 35.0:
			failures.append("%s did not patrol from %s to %s" % [actor.get("id", "raider"), str(start), str(raider.position)])
		raider.queue_free()
	if failures.is_empty():
		print("AI behavior check OK")
		quit()
	for failure: String in failures:
		push_error(failure)
	quit()
