import random
from collections import defaultdict
from math import ceil


def select_proportional_races(
    races: list[dict], total_to_select: int = 10
) -> list[dict]:
    if len(races) < total_to_select:
        return []

    races_by_distance = defaultdict(list)
    for race in races:
        distance = race.get("distance") or "unknown"
        races_by_distance[distance].append(race)

    total_races = sum(len(items) for items in races_by_distance.values())
    if total_races < total_to_select:
        return []

    selected_races: list[dict] = []
    for race_list in races_by_distance.values():
        portion = len(race_list) / total_races
        num_to_pick = max(1, ceil(portion * total_to_select))
        selected_races.extend(
            random.sample(race_list, min(num_to_pick, len(race_list)))
        )

    unique_races_by_id = {}
    for race in selected_races:
        unique_races_by_id[race["_id"]] = race
    selected_races = list(unique_races_by_id.values())

    if len(selected_races) < total_to_select:
        selected_ids = {race["_id"] for race in selected_races}
        remaining = [race for race in races if race["_id"] not in selected_ids]
        if remaining:
            needed = total_to_select - len(selected_races)
            selected_races.extend(random.sample(remaining, min(needed, len(remaining))))

    if len(selected_races) < total_to_select:
        return []
    if len(selected_races) > total_to_select:
        selected_races = random.sample(selected_races, total_to_select)
    return selected_races


def format_game_races(selected_races: list[dict]) -> list[dict]:
    formatted = []
    for i, race in enumerate(selected_races, start=1):
        formatted.append(
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
    return formatted
