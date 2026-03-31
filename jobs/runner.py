from __future__ import annotations

import os
import select
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

from jobs.service import (
    append_job_log,
    claim_next_job,
    complete_job,
    get_race_count,
    get_job_command,
    get_repo_root,
    init_job_indexes,
    is_cancel_requested,
    mark_stale_running_jobs,
    MIN_REQUIRED_RACES,
    set_job_pid,
    update_job_heartbeat,
)


def run_worker_loop(poll_interval: float = 2.0) -> None:
    load_dotenv()
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["horseRacingGame"]
    init_job_indexes(db)

    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    repo_root: Path = get_repo_root()

    while True:
        mark_stale_running_jobs(db)
        job = claim_next_job(db, worker_id=worker_id)
        if not job:
            time.sleep(poll_interval)
            continue

        job_id = job["_id"]
        seq = int(job.get("last_log_seq", 0))
        job_type = job["job_type"]

        try:
            command = [sys.executable, "-u", *get_job_command(job_type, repo_root)]
            proc = subprocess.Popen(
                command,
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            set_job_pid(db, job_id, proc.pid)

            assert proc.stdout is not None
            cancelled = False
            while proc.poll() is None:
                if is_cancel_requested(db, job_id):
                    proc.terminate()
                    cancelled = True
                    seq += 1
                    append_job_log(
                        db,
                        job_id=job_id,
                        seq=seq,
                        line="[worker] Cancellation requested. Terminating process...",
                        stream="stderr",
                    )
                    break

                ready, _, _ = select.select([proc.stdout], [], [], 1.0)
                if ready:
                    line = proc.stdout.readline()
                    if line:
                        seq += 1
                        append_job_log(
                            db,
                            job_id=job_id,
                            seq=seq,
                            line=line,
                            stream="stdout",
                        )
                update_job_heartbeat(db, job_id)

            for line in proc.stdout:
                seq += 1
                append_job_log(db, job_id=job_id, seq=seq, line=line, stream="stdout")

            exit_code = proc.wait()
            if cancelled:
                complete_job(
                    db,
                    job_id,
                    status="cancelled",
                    exit_code=exit_code,
                    error_message="Cancelled by user.",
                )
            elif exit_code == 0:
                complete_job(db, job_id, status="succeeded", exit_code=exit_code)
            else:
                race_count_after = get_race_count(db)
                reached_minimum = race_count_after >= MIN_REQUIRED_RACES
                if job_type == "scrape_races" and reached_minimum:
                    complete_job(
                        db,
                        job_id,
                        status="succeeded",
                        exit_code=exit_code,
                        error_message=(
                            "Script exited early but minimum races were reached."
                        ),
                    )
                    continue
                complete_job(
                    db,
                    job_id,
                    status="failed",
                    exit_code=exit_code,
                    error_message=f"Script exited with code {exit_code}.",
                )
        except Exception as exc:  # noqa: BLE001
            seq += 1
            append_job_log(
                db,
                job_id=job_id,
                seq=seq,
                line=f"[worker-error] {exc}",
                stream="stderr",
            )
            complete_job(
                db,
                job_id,
                status="failed",
                exit_code=1,
                error_message=str(exc),
            )


if __name__ == "__main__":
    run_worker_loop()
