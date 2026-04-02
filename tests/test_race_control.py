import unittest

from controllers.race_control import get_games_badge_variant, get_games_left


class RaceControlHelpersTests(unittest.TestCase):
    def test_get_games_left_uses_floor_division(self):
        self.assertEqual(get_games_left(0), 0)
        self.assertEqual(get_games_left(9), 0)
        self.assertEqual(get_games_left(10), 1)
        self.assertEqual(get_games_left(19), 1)
        self.assertEqual(get_games_left(20), 2)

    def test_get_games_left_handles_invalid_divisor(self):
        self.assertEqual(get_games_left(50, races_per_game=0), 0)

    def test_get_games_badge_variant_thresholds(self):
        self.assertEqual(get_games_badge_variant(0), "danger")
        self.assertEqual(get_games_badge_variant(1), "danger")
        self.assertEqual(get_games_badge_variant(2), "warning")
        self.assertEqual(get_games_badge_variant(15), "warning")
        self.assertEqual(get_games_badge_variant(16), "warning")
        self.assertEqual(get_games_badge_variant(17), "success")


if __name__ == "__main__":
    unittest.main()
