from __future__ import annotations

import os
import socket
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dotenv import load_dotenv


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_worker_id() -> str:
    return os.getenv("WORKER_ID") or socket.gethostname()


def get_max_age_seconds() -> int:
    raw = os.getenv("WORKER_HEALTH_MAX_AGE_SECONDS", "90")
    try:
        value = int(raw)
        return value if value > 0 else 90
    except ValueError:
        return 90


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_worker_healthy(
    db: Any, worker_id: str, max_age_seconds: int
) -> tuple[bool, str]:
    doc: Optional[dict[str, Any]] = db.worker_heartbeats.find_one(
        {"worker_id": worker_id},
        {"updated_at": 1},
    )
    if not doc:
        return False, f"worker heartbeat not found for worker_id={worker_id}"

    updated_at = doc.get("updated_at")
    if not isinstance(updated_at, datetime):
        return False, "worker heartbeat missing updated_at"

    age = _utc_now() - _as_utc(updated_at)
    if age > timedelta(seconds=max_age_seconds):
        return (
            False,
            f"worker heartbeat stale: age={int(age.total_seconds())}s "
            f"max={max_age_seconds}s",
        )

    return True, "ok"


def main() -> int:
    load_dotenv()

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("MONGODB_URI is not set", file=sys.stderr)
        return 1

    worker_id = get_worker_id()
    max_age_seconds = get_max_age_seconds()
    client = None

    try:
        from pymongo import MongoClient

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client["horseRacingGame"]
        healthy, reason = is_worker_healthy(db, worker_id, max_age_seconds)
        if healthy:
            return 0
        print(reason, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"healthcheck error: {exc}", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
