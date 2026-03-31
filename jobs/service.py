from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from signal import SIGTERM
from typing import Any, Optional

from bson import ObjectId
from pymongo import ReturnDocument

MIN_REQUIRED_RACES = 10
ACTIVE_JOB_STATUSES = ("queued", "running")
VALID_JOB_TYPES = ("scrape_races", "move_races")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_job_command(job_type: str, repo_root: Optional[Path] = None) -> list[str]:
    root = repo_root or get_repo_root()
    scripts = {
        "scrape_races": root / "races_scraper" / "races_scraper.py",
        "move_races": root / "races_scraper" / "util" / "move_races.py",
    }
    script_path = scripts.get(job_type)
    if script_path is None:
        raise ValueError(f"Unsupported job_type: {job_type}")
    return [str(script_path)]


def init_job_indexes(db: Any) -> None:
    db.jobs.create_index("status")
    db.jobs.create_index("created_at")
    db.jobs.create_index("heartbeat_at")
    db.job_logs.create_index([("job_id", 1), ("seq", 1)], unique=True)
    db.job_logs.create_index("ts")


def get_race_count(db: Any) -> int:
    return db.races.count_documents({})


def has_minimum_races(db: Any, minimum: int = MIN_REQUIRED_RACES) -> bool:
    return get_race_count(db) >= minimum


def parse_job_id(job_id: str) -> ObjectId:
    return ObjectId(job_id)


def serialize_job(job: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not job:
        return None
    serialized = dict(job)
    serialized["id"] = str(serialized.pop("_id"))
    for key, value in list(serialized.items()):
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
    return serialized


def get_active_job(db: Any) -> Optional[dict[str, Any]]:
    return db.jobs.find_one(
        {"status": {"$in": ACTIVE_JOB_STATUSES}},
        sort=[("created_at", -1)],
    )


def enqueue_job(
    db: Any,
    job_type: str,
    requested_by: str = "web-ui",
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    if job_type not in VALID_JOB_TYPES:
        raise ValueError(f"Unsupported job_type: {job_type}")

    active_job = get_active_job(db)
    if active_job:
        return None, active_job

    created_at = utc_now()
    race_count_before = get_race_count(db)
    job = {
        "job_type": job_type,
        "status": "queued",
        "created_at": created_at,
        "started_at": None,
        "finished_at": None,
        "worker_id": None,
        "pid": None,
        "exit_code": None,
        "error_message": None,
        "requested_by": requested_by,
        "race_count_before": race_count_before,
        "race_count_after": None,
        "last_log_seq": 0,
        "heartbeat_at": None,
        "cancel_requested": False,
        "cancel_requested_at": None,
    }
    insert_result = db.jobs.insert_one(job)
    job["_id"] = insert_result.inserted_id
    return job, None


def claim_next_job(db: Any, worker_id: str) -> Optional[dict[str, Any]]:
    now = utc_now()
    return db.jobs.find_one_and_update(
        {"status": "queued", "cancel_requested": {"$ne": True}},
        {
            "$set": {
                "status": "running",
                "started_at": now,
                "heartbeat_at": now,
                "worker_id": worker_id,
            }
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )


def set_job_pid(db: Any, job_id: ObjectId, pid: int) -> None:
    db.jobs.update_one({"_id": job_id}, {"$set": {"pid": pid}})


def update_job_heartbeat(db: Any, job_id: ObjectId) -> None:
    db.jobs.update_one({"_id": job_id}, {"$set": {"heartbeat_at": utc_now()}})


def append_job_log(
    db: Any,
    job_id: ObjectId,
    seq: int,
    line: str,
    stream: str = "stdout",
) -> None:
    sanitized = line.rstrip("\r\n")[:1200]
    db.job_logs.insert_one(
        {
            "job_id": job_id,
            "seq": seq,
            "ts": utc_now(),
            "stream": stream,
            "line": sanitized,
        }
    )
    db.jobs.update_one(
        {"_id": job_id},
        {"$set": {"last_log_seq": seq, "heartbeat_at": utc_now()}},
    )


def complete_job(
    db: Any,
    job_id: ObjectId,
    status: str,
    exit_code: int,
    error_message: Optional[str] = None,
) -> None:
    race_count_after = get_race_count(db)
    db.jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": status,
                "exit_code": exit_code,
                "error_message": error_message,
                "finished_at": utc_now(),
                "race_count_after": race_count_after,
                "heartbeat_at": utc_now(),
            }
        },
    )


def mark_stale_running_jobs(
    db: Any,
    stale_after_seconds: int = 120,
) -> int:
    stale_before = utc_now() - timedelta(seconds=stale_after_seconds)
    result = db.jobs.update_many(
        {
            "status": "running",
            "$or": [
                {"heartbeat_at": {"$lt": stale_before}},
                {"heartbeat_at": None},
            ],
        },
        {
            "$set": {
                "status": "failed",
                "finished_at": utc_now(),
                "error_message": "Marked stale after worker heartbeat timeout.",
            }
        },
    )
    return int(result.modified_count)


def get_job_by_id(db: Any, job_id: str) -> Optional[dict[str, Any]]:
    return db.jobs.find_one({"_id": parse_job_id(job_id)})


def is_cancel_requested(db: Any, job_id: ObjectId) -> bool:
    job = db.jobs.find_one({"_id": job_id}, {"cancel_requested": 1})
    return bool(job and job.get("cancel_requested"))


def request_job_cancel(db: Any, job_id: str) -> tuple[Optional[dict[str, Any]], str]:
    oid = parse_job_id(job_id)
    job = db.jobs.find_one({"_id": oid})
    if not job:
        return None, "not_found"

    status = job.get("status")
    if status not in {"queued", "running"}:
        return job, "already_finished"

    now = utc_now()
    if status == "queued":
        updated = db.jobs.find_one_and_update(
            {"_id": oid, "status": "queued"},
            {
                "$set": {
                    "status": "cancelled",
                    "cancel_requested": True,
                    "cancel_requested_at": now,
                    "finished_at": now,
                    "error_message": "Cancelled by user before start.",
                    "exit_code": 143,
                    "race_count_after": get_race_count(db),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return updated, "cancelled"

    updated = db.jobs.find_one_and_update(
        {"_id": oid, "status": "running"},
        {
            "$set": {
                "cancel_requested": True,
                "cancel_requested_at": now,
                "error_message": "Cancellation requested by user.",
                "signal": int(SIGTERM),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return updated, "cancelling"


def get_logs_after_seq(
    db: Any,
    job_id: str,
    after_seq: int,
    limit: int = 500,
) -> list[dict[str, Any]]:
    oid = parse_job_id(job_id)
    logs = db.job_logs.find(
        {"job_id": oid, "seq": {"$gt": after_seq}},
        sort=[("seq", 1)],
        limit=max(1, min(limit, 2000)),
    )
    return list(logs)
