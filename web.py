import os
import threading
import time

from dotenv import load_dotenv
from flask import Flask
from pymongo import MongoClient

from controllers.race_control import race_control
from jobs.runner import run_worker_loop
from jobs.service import init_job_indexes

load_dotenv()

_worker_lock = threading.Lock()
_worker_started = False


def is_production_env() -> bool:
    return os.getenv("ENV", "").lower() == "production"


def should_start_dev_worker() -> bool:
    if is_production_env():
        return False

    auto_start = os.getenv("AUTO_START_JOB_WORKER", "true").lower()
    if auto_start in {"0", "false", "no"}:
        return False

    from_cli = os.getenv("FLASK_RUN_FROM_CLI") == "true"
    reloader_main = os.getenv("WERKZEUG_RUN_MAIN")
    if from_cli and reloader_main != "true":
        return False

    return True


def start_dev_worker_if_needed() -> None:
    global _worker_started

    if not should_start_dev_worker():
        return

    with _worker_lock:
        if _worker_started:
            return

        worker_thread = threading.Thread(
            target=run_worker_loop,
            kwargs={"poll_interval": 2.0},
            daemon=True,
            name="mongo-job-worker",
        )
        worker_thread.start()
        _worker_started = True


def create_app():
    app = Flask(__name__)

    app.config["MONGODB_URI"] = os.environ.get("MONGODB_URI")
    app.db = MongoClient(app.config["MONGODB_URI"]).get_default_database()
    init_job_indexes(app.db)

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "Missing required SECRET_KEY environment variable. "
            "Set SECRET_KEY in your .env file before starting the app."
        )

    app.config["SECRET_KEY"] = secret_key
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["ASSET_VERSION"] = os.getenv("ASSET_VERSION", str(int(time.time())))

    @app.context_processor
    def inject_asset_version():
        return {"asset_version": app.config["ASSET_VERSION"]}

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "horse-racing-game"}, 200

    app.register_blueprint(race_control)
    start_dev_worker_if_needed()

    return app


if __name__ == "__main__":
    flask_app = create_app()
    port = int(os.getenv("PORT", "3008"))
    flask_app.run(
        host="0.0.0.0",
        port=port,
        debug=not is_production_env(),
        use_reloader=False,
    )
