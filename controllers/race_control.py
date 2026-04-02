from bson.errors import InvalidId
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
)

from controllers.game_logic import format_game_races, select_proportional_races
from jobs.service import (
    MIN_REQUIRED_RACES,
    enqueue_job,
    get_active_job,
    get_job_by_id,
    get_logs_after_seq,
    get_race_count,
    has_minimum_races,
    request_job_cancel,
    serialize_job,
)

race_control = Blueprint(
    "race_control", __name__, template_folder="templates", static_folder="static"
)

RACES_PER_GAME = 10


def get_game_state() -> dict:
    return current_app.db.game_races.find_one({}) or {"game_tracker": 0, "races": []}


def get_game_tracker() -> int:
    return int(get_game_state().get("game_tracker", 0))


def get_games_left(total_races: int, races_per_game: int = RACES_PER_GAME) -> int:
    if races_per_game <= 0:
        return 0
    return max(0, total_races // races_per_game)


def get_games_badge_variant(games_left: int) -> str:
    if games_left <= 1:
        return "danger"
    if games_left <= 16:
        return "warning"
    return "success"


def choose_game_races(total_to_select: int = 10) -> list[dict]:
    races = list(current_app.db.races.find({}))
    return select_proportional_races(races, total_to_select=total_to_select)


def initialize_new_game(total_to_select: int = 10) -> bool:
    selected_races = choose_game_races(total_to_select=total_to_select)
    if len(selected_races) != total_to_select:
        return False

    formatted_races = format_game_races(selected_races)

    current_app.db.game_races.delete_many({})
    current_app.db.game_races.insert_one({"game_tracker": 1, "races": formatted_races})

    selected_ids = [race["_id"] for race in selected_races]
    original_races = list(current_app.db.races.find({"_id": {"$in": selected_ids}}))
    if original_races:
        result = current_app.db.played_races.insert_many(original_races)
        if result.inserted_ids and len(result.inserted_ids) == len(original_races):
            current_app.db.races.delete_many({"_id": {"$in": selected_ids}})

    return True


def normalize_job(job: dict | None) -> dict | None:
    serialized = serialize_job(job)
    if not serialized:
        return None
    serialized["is_active"] = serialized.get("status") in {"queued", "running"}
    return serialized


@race_control.route("/", methods=["GET"])
def index():
    game_tracker = get_game_tracker()
    total_races = get_race_count(current_app.db)
    games_left = get_games_left(total_races)
    games_badge_variant = get_games_badge_variant(games_left)

    return render_template(
        "index.html",
        title="Home",
        game_tracker=game_tracker,
        total_races=total_races,
        games_left=games_left,
        games_badge_variant=games_badge_variant,
        min_required=MIN_REQUIRED_RACES,
    )


@race_control.route("/game_config", methods=["GET"])
def game_config():
    game_tracker = get_game_tracker()
    restart = request.args.get("restart") == "true"
    if restart and game_tracker != 0:
        if not has_minimum_races(current_app.db, MIN_REQUIRED_RACES):
            flash(
                "Cannot start a new game yet. "
                "Continue the current game or add more races.",
                "warning",
            )
            return redirect("/")
        flash("Game restarted", "success")
        game_tracker = 0

    if game_tracker == 0:
        if not has_minimum_races(current_app.db, MIN_REQUIRED_RACES):
            flash(
                f"At least {MIN_REQUIRED_RACES} races are required "
                "to start a new game.",
                "warning",
            )
            return redirect("/")
        if not initialize_new_game(total_to_select=10):
            flash(
                "Unable to create a full 10-race game from available races.",
                "warning",
            )
            return redirect("/")
    elif game_tracker == 10:
        return redirect("/finished")
    elif game_tracker < 0 or game_tracker > 10:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")
    else:
        current_app.db.game_races.update_one({}, {"$inc": {"game_tracker": 1}})

    return redirect("/hrg")


@race_control.route("/hrg", methods=["GET"])
def hrg():
    game_races = get_game_state()
    game_tracker = int(game_races.get("game_tracker", 0))

    continued = request.args.get("continued")
    if continued == "true":
        flash(f"Game resumed from Race {game_tracker}", "success")

    if game_tracker == 0:
        return redirect("/")
    elif game_tracker < 0 or game_tracker > 10:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")

    current_race = None
    for race in game_races.get("races"):
        if race.get("race_number") == game_tracker:
            current_race = race

    if current_race is None:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        flash("Game data is missing for the current race.", "warning")
        return redirect("/")

    return render_template(
        "hrg.html",
        title=f"Race {game_tracker}",
        current_race=current_race,
        game_tracker=game_tracker,
    )


@race_control.route("/race_result", methods=["GET"])
def race_result():
    game_races = get_game_state()
    game_tracker = int(game_races.get("game_tracker", 0))

    if game_tracker == 0:
        return redirect("/")
    elif game_tracker < 0 or game_tracker > 10:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")

    current_race = None
    for race in game_races.get("races"):
        if race.get("race_number") == game_tracker:
            current_race = race

    if current_race is None:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        flash("Game data is missing for the current race.", "warning")
        return redirect("/")

    return render_template(
        "race_result.html",
        title=f"Race {game_tracker} Result",
        current_race=current_race,
        game_tracker=game_tracker,
    )


@race_control.route("/finished", methods=["GET"])
def finished():
    game_races = get_game_state()
    game_tracker = int(game_races.get("game_tracker", 0))

    if game_tracker == 0:
        return redirect("/")
    elif game_tracker < 0 or game_tracker > 10:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")

    current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})

    return render_template("finished.html", title="Game Finished")


@race_control.route("/test_flash")
def test_flash():
    flash("This is a test flash", "success")
    return redirect("/hrg")


@race_control.route("/scraper", methods=["GET"])
def scraper():
    race_count = get_race_count(current_app.db)
    game_tracker = get_game_tracker()
    active_job = normalize_job(get_active_job(current_app.db))

    return render_template(
        "scraper.html",
        title="Race Scraper",
        race_count=race_count,
        min_required=MIN_REQUIRED_RACES,
        game_tracker=game_tracker,
        active_job=active_job,
    )


@race_control.route("/api/races/count", methods=["GET"])
def api_race_count():
    race_count = get_race_count(current_app.db)
    return jsonify(
        {
            "count": race_count,
            "min_required": MIN_REQUIRED_RACES,
            "enough": race_count >= MIN_REQUIRED_RACES,
        }
    )


@race_control.route("/api/jobs", methods=["POST"])
def api_create_job():
    payload = request.get_json(silent=True) or {}
    job_type = str(payload.get("job_type", "")).strip()

    try:
        queued_job, active_job = enqueue_job(current_app.db, job_type=job_type)
    except ValueError:
        return jsonify({"error": "Unsupported job_type"}), 400

    if active_job:
        return (
            jsonify(
                {
                    "error": "An active job already exists",
                    "active_job": normalize_job(active_job),
                }
            ),
            409,
        )

    return jsonify({"job": normalize_job(queued_job)}), 201


@race_control.route("/api/jobs/active", methods=["GET"])
def api_active_job():
    active_job = get_active_job(current_app.db)
    return jsonify({"job": normalize_job(active_job)})


@race_control.route("/api/jobs/<job_id>", methods=["GET"])
def api_get_job(job_id):
    try:
        job = get_job_by_id(current_app.db, job_id)
    except InvalidId:
        return jsonify({"error": "Invalid job id"}), 400

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"job": normalize_job(job)})


@race_control.route("/api/jobs/<job_id>/logs", methods=["GET"])
def api_get_job_logs(job_id):
    try:
        job = get_job_by_id(current_app.db, job_id)
    except InvalidId:
        return jsonify({"error": "Invalid job id"}), 400

    if not job:
        return jsonify({"error": "Job not found"}), 404

    try:
        after_seq = int(request.args.get("after_seq", 0))
    except ValueError:
        return jsonify({"error": "after_seq must be an integer"}), 400

    logs = get_logs_after_seq(current_app.db, job_id=job_id, after_seq=after_seq)
    lines = [
        {
            "seq": row["seq"],
            "ts": row["ts"].isoformat() if row.get("ts") else None,
            "stream": row.get("stream", "stdout"),
            "line": row.get("line", ""),
        }
        for row in logs
    ]
    next_seq = lines[-1]["seq"] if lines else after_seq

    return jsonify(
        {
            "job": normalize_job(job),
            "lines": lines,
            "next_seq": next_seq,
        }
    )


@race_control.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def api_cancel_job(job_id):
    try:
        updated_job, result = request_job_cancel(current_app.db, job_id)
    except InvalidId:
        return jsonify({"error": "Invalid job id"}), 400

    if result == "not_found":
        return jsonify({"error": "Job not found"}), 404

    if result == "already_finished":
        return (
            jsonify(
                {
                    "error": "Job is not active",
                    "job": normalize_job(updated_job),
                }
            ),
            409,
        )

    return jsonify({"job": normalize_job(updated_job), "result": result})
