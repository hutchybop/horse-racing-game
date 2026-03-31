import random
import unittest

from controllers.game_logic import format_game_races, select_proportional_races


def build_race(race_id: int, distance: str) -> dict:
    return {
        "_id": race_id,
        "title": f"Race {race_id}",
        "course": "Test Course",
        "date": "2026-01-01 12:00:00",
        "distance": distance,
        "racing_tv_url": f"https://example.com/{race_id}",
        "horses": [],
    }


class GameLogicTests(unittest.TestCase):
    def setUp(self):
        random.seed(42)

    def test_select_proportional_races_returns_exact_target(self):
        races = []
        races.extend(build_race(i, "1m") for i in range(1, 9))
        races.extend(build_race(i, "7f") for i in range(9, 15))
        races.extend(build_race(i, "2m") for i in range(15, 21))

        selected = select_proportional_races(races, total_to_select=10)
        self.assertEqual(len(selected), 10)
        self.assertEqual(len({race["_id"] for race in selected}), 10)

    def test_select_proportional_races_returns_empty_when_pool_too_small(self):
        races = [build_race(i, "1m") for i in range(1, 8)]
        selected = select_proportional_races(races, total_to_select=10)
        self.assertEqual(selected, [])

    def test_select_proportional_races_handles_missing_distance(self):
        races = [
            build_race(1, "1m"),
            build_race(2, "1m"),
            build_race(3, "1m"),
            build_race(4, "1m"),
            build_race(5, "1m"),
            build_race(6, "1m"),
            build_race(7, "1m"),
            build_race(8, "1m"),
            {
                **build_race(9, ""),
                "distance": None,
            },
            {
                **build_race(10, ""),
                "distance": None,
            },
        ]
        selected = select_proportional_races(races, total_to_select=10)
        self.assertEqual(len(selected), 10)

    def test_format_game_races_numbers_in_sequence(self):
        selected = [build_race(i, "1m") for i in range(1, 4)]
        formatted = format_game_races(selected)
        self.assertEqual([row["race_number"] for row in formatted], [1, 2, 3])
        self.assertEqual(formatted[0]["title"], "Race 1")


if __name__ == "__main__":
    unittest.main()
