import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from jobs.worker_healthcheck import get_max_age_seconds, is_worker_healthy


class _FakeCollection:
    def __init__(self, doc):
        self.doc = doc

    def find_one(self, *_args, **_kwargs):
        return self.doc


class _FakeDB:
    def __init__(self, doc):
        self.worker_heartbeats = _FakeCollection(doc)


class WorkerHealthcheckTests(unittest.TestCase):
    def test_get_max_age_seconds_default_on_invalid(self):
        with patch.dict(
            os.environ, {"WORKER_HEALTH_MAX_AGE_SECONDS": "nope"}, clear=False
        ):
            self.assertEqual(get_max_age_seconds(), 90)

    def test_get_max_age_seconds_uses_positive_int(self):
        with patch.dict(
            os.environ, {"WORKER_HEALTH_MAX_AGE_SECONDS": "120"}, clear=False
        ):
            self.assertEqual(get_max_age_seconds(), 120)

    def test_is_worker_healthy_when_recent_heartbeat(self):
        db = _FakeDB(
            {
                "updated_at": datetime.now(timezone.utc) - timedelta(seconds=10),
            }
        )
        healthy, reason = is_worker_healthy(
            db, worker_id="worker-1", max_age_seconds=90
        )
        self.assertTrue(healthy)
        self.assertEqual(reason, "ok")

    def test_is_worker_unhealthy_when_stale(self):
        db = _FakeDB(
            {
                "updated_at": datetime.now(timezone.utc) - timedelta(seconds=300),
            }
        )
        healthy, reason = is_worker_healthy(
            db, worker_id="worker-1", max_age_seconds=90
        )
        self.assertFalse(healthy)
        self.assertIn("stale", reason)

    def test_is_worker_unhealthy_when_missing(self):
        db = _FakeDB(None)
        healthy, reason = is_worker_healthy(
            db, worker_id="worker-1", max_age_seconds=90
        )
        self.assertFalse(healthy)
        self.assertIn("not found", reason)


if __name__ == "__main__":
    unittest.main()
