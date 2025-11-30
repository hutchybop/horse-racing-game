import random
from flask import Blueprint, render_template, current_app, request, redirect, flash
from math import ceil
from collections import defaultdict

race_control = Blueprint(
    "race_control", __name__, template_folder="templates", static_folder="static"
)


@race_control.route("/", methods=["GET"])
def index():

    game_races = current_app.db.game_races.find_one({})
    game_tracker = game_races.get("game_tracker", 0)

    return render_template("index.html", title="Home", game_tracker=game_tracker)


@race_control.route("/game_config", methods=["GET"])
def game_config():

    restart = request.args.get("restart")
    # Restart the game
    if restart == "true":
        flash("Game restarted", "success")
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})

    game_races = current_app.db.game_races.find_one({})
    game_tracker = game_races.get("game_tracker", 0)
    # Create the game if game_tracker is 0
    if game_tracker == 0:
        # --- 1️⃣ Fetch and group races by distance ---
        races = list(current_app.db.races.find({}))
        races_by_distance = defaultdict(list)
        for race in races:
            distance = race.get("distance")
            if distance:
                races_by_distance[distance].append(race)

        # --- 2️⃣ Figure out how many races exist per distance ---
        counts = {
            distance: len(race_list)
            for distance, race_list in races_by_distance.items()
        }
        total_races = sum(counts.values())

        # --- 3️⃣ Select proportionally based on total ---
        total_to_select = 10
        selected_races = []

        for distance, race_list in races_by_distance.items():
            # Calculate the proportion of races at this distance
            portion = len(race_list) / total_races
            # Decide how many to pick from this distance
            num_to_pick = max(1, ceil(portion * total_to_select))
            # Randomly choose that many races from the group
            selected_races += random.sample(race_list, min(num_to_pick, len(race_list)))

        # --- 4️⃣ Make sure we have exactly 10 races ---
        selected_races = random.sample(selected_races, 10)

        # --- 5️⃣ Format races and reset the game document ---
        formatted_races = []
        for i, race in enumerate(selected_races, start=1):
            formatted_races.append(
                {
                    "race_number": i,
                    "title": race.get("title"),
                    "course": race.get("course"),
                    "date": race.get("date"),
                    "distance": race.get("distance"),
                    "racing_tv_url": race.get("racing_tv_url"),
                    "horses": race.get("horses", []),
                }
            )

        # Remove existing game_races doc and insert new one
        current_app.db.game_races.delete_many({})  # clear old game state
        current_app.db.game_races.insert_one(
            {"game_tracker": game_tracker + 1, "races": formatted_races}
        )

        # --- 6️⃣ Move selected races to played_races ---
        # Collect selected race IDs
        selected_ids = [race["_id"] for race in selected_races]

        # Fetch their full documents from the master races collection
        original_races = list(current_app.db.races.find({"_id": {"$in": selected_ids}}))

        # Insert into played_races first, only then delete from races
        if original_races:
            result = current_app.db.played_races.insert_many(original_races)
            if result.inserted_ids and len(result.inserted_ids) == len(original_races):
                # Only delete if all races were inserted successfully
                current_app.db.races.delete_many({"_id": {"$in": selected_ids}})
    elif game_tracker == 10:
        #   The game has finished
        return redirect("/finished")
    elif game_tracker < 0 or game_tracker > 10:
        # If the game_tracker is not between 1 or 10 reset it and return to index
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")
    else:
        # If game_tracker is not 0 just increase by 1
        current_app.db.game_races.update_one({}, {"$inc": {"game_tracker": 1}})

    return redirect("/hrg")


@race_control.route("/hrg", methods=["GET"])
def hrg():

    game_races = current_app.db.game_races.find_one({})
    game_tracker = game_races.get("game_tracker", 0)

    continued = request.args.get("continued")
    # Restart the game
    if continued == "true":
        flash(f"Game resumed from Race {game_tracker}", "success")

    # If no game is in progress ie game_tracker is 0, return to index
    #  Or if the game_tracker is not between 1 or 10 reset it and return to index
    if game_tracker == 0:
        return redirect("/")
    elif game_tracker < 0 or game_tracker > 10:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")

    for race in game_races.get("races"):
        if race.get("race_number") == game_tracker:
            current_race = race

    return render_template(
        "hrg.html",
        title=f"Race {game_tracker}",
        current_race=current_race,
        game_tracker=game_tracker,
    )


@race_control.route("/race_result", methods=["GET"])
def race_result():
    game_races = current_app.db.game_races.find_one({})
    game_tracker = game_races.get("game_tracker", 0)

    # If no game is in progress ie game_tracker is 0, return to index
    #  Or if the game_tracker is not between 1 or 10 reset it and return to index
    if game_tracker == 0:
        return redirect("/")
    elif game_tracker < 0 or game_tracker > 10:
        current_app.db.game_races.update_one({}, {"$set": {"game_tracker": 0}})
        return redirect("/")

    for race in game_races.get("races"):
        if race.get("race_number") == game_tracker:
            current_race = race

    return render_template(
        "race_result.html",
        title=f"Race {game_tracker} Result",
        current_race=current_race,
        game_tracker=game_tracker,
    )


@race_control.route("/finished", methods=["GET"])
def finished():
    game_races = current_app.db.game_races.find_one({})
    game_tracker = game_races.get("game_tracker", 0)

    # If no game is in progress ie game_tracker is 0, return to index
    #  Or if the game_tracker is not between 1 or 10 reset it and return to index
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
