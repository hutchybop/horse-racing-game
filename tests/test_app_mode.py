import os
import unittest
from unittest.mock import patch

from web import is_production_env, should_start_dev_worker


class AppModeTests(unittest.TestCase):
    def test_is_production_env_true(self):
        with patch.dict(os.environ, {"ENV": "production"}, clear=False):
            self.assertTrue(is_production_env())

    def test_is_production_env_false_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_production_env())

    def test_should_start_dev_worker_local_cli_child(self):
        with patch.dict(
            os.environ,
            {
                "FLASK_RUN_FROM_CLI": "true",
                "WERKZEUG_RUN_MAIN": "true",
            },
            clear=True,
        ):
            self.assertTrue(should_start_dev_worker())

    def test_should_not_start_dev_worker_cli_reloader_parent(self):
        with patch.dict(
            os.environ,
            {
                "FLASK_RUN_FROM_CLI": "true",
            },
            clear=True,
        ):
            self.assertFalse(should_start_dev_worker())

    def test_should_not_start_dev_worker_in_production(self):
        with patch.dict(
            os.environ,
            {
                "ENV": "production",
                "FLASK_RUN_FROM_CLI": "true",
                "WERKZEUG_RUN_MAIN": "true",
            },
            clear=True,
        ):
            self.assertFalse(should_start_dev_worker())


if __name__ == "__main__":
    unittest.main()
