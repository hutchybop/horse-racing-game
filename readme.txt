# ---------------Usage---------------

Make sure python env is set:
    source <env name>/bin/activate

Make sure .env has correct keys - see below

Check Mongodb horseRacingGame:
    races - has 10 or more races
    If not, run:
        races_scraper/races_scraper.py
        Should be able to scrape enough races, might take 20-25 mins
        If fails and races in played_races run: 
            races_scraper/move_races.py

Run flask (from root):
    flask run
    Then go to: http://127.0.0.1:5000/


# ---------- Initial setup ----------

Create python enviroment and enable:
    change directory to project root
    python3 -m venv hrg_env
    source <env name>/bin/activate

Install required packages:
    pip3 install --upgrade pip setuptools wheel
    pip3 install -r requirements.txt

Install playwright (for server look at requirements.txt):
    python -m playwright install

Setup .env:
    create .env in project root if not already there.
    Add:
        ALT_SCRAPER_PATH  # Path to scraper log if required - Optional
        MONGODB_URI # for horceRacingGame db
        API_KEY_1 # from rapidapi.com - horse racing
        SECRET_KEY # key for session


# ---------- Mongodb horseRacinGame DB config ----------

races
    Holds race dicts used for the game
    Populated by races_scraper.py

race_index
    Holds race ids from rapidapi and the last date to be scraped
    Used by races_scraper.py and checked by check_races.py / condition_counter.py

game_races
    Holds 10 races and game tracker for game
    Populated from races by web app

played_races
    Holds all races already played
    Filled during gameplay; util scripts can move some/all back to races

races_backup
    Backup copy of races before distance cleanup deletes are run
    Created/used by util/less_2m_delete.py

races_backup_testing
    Temporary backup store for testing with a reduced races set
    Created by util/backup_for_testing.py and restored by util/restore_from_testing_backup.py

played_backup
    Backup snapshot of played_races
    Created by util/backup_palyed.py and referenced by util/restored_played.py

jobs
    Job queue docs for scraper actions (queued/running/succeeded/failed)
    Used by jobs.runner + web job endpoints

job_logs
    Per-job log lines for background job output
    Written by jobs.runner and read by scraper job APIs

worker_heartbeats
    Worker heartbeat timestamps and status for worker health checks
    Written by jobs.runner and checked by jobs.worker_healthcheck


# ----------------- Scripts and logs -----------------

races_scraper.py
    Will get races from rapidapi.com
    Standalone: Yes
    Depends on scraper scripts: None
    Used by scraper scripts: check_races.py validates its output data
    Checks:
        racing tv video is avaiable
        number of horses is between 2-8 - ensure all data fits on screen
        race distance is 2m or under - stops long race times on replay
        checks all race fields are present

check_races.py
    Re-validates all races currently in races and logs any issues found
    Standalone: Yes
    Depends on scraper scripts: Uses data produced by races_scraper.py
    Used by scraper scripts: None

util/move_races.py
    Moves old races from payed_races to races
    Default is 10 - can be changed in fields
    Allows old races to be used if scraper fails
    Standalone: Yes
    Depends on scraper scripts: None
    Used by scraper scripts: None

util/less_2m_delete.py
    Backs up races to races_backup, then removes races over 2 miles
    Standalone: Yes
    Depends on scraper scripts: Uses races usually populated by races_scraper.py
    Used by scraper scripts: None

util/condition_counter.py
    Prints simple counts for race fields (course/date/distance/horse count)
    Standalone: Yes
    Depends on scraper scripts: Uses races usually populated by races_scraper.py
    Used by scraper scripts: None

util/backup_for_testing.py
    Moves most races to races_backup_testing and keeps a small set in races
    Standalone: Yes
    Depends on scraper scripts: Uses races usually populated by races_scraper.py
    Used by scraper scripts: util/restore_from_testing_backup.py

util/restore_from_testing_backup.py
    Restores races from races_backup_testing back into races
    Standalone: Yes
    Depends on scraper scripts: Expects backup created by util/backup_for_testing.py
    Used by scraper scripts: None

util/backup_palyed.py
    Copies all played_races into played_backup for safe restore workflows
    Standalone: Yes
    Depends on scraper scripts: None
    Used by scraper scripts: util/restored_played.py

util/restored_played.py
    Moves newer played races back to races using played_backup as baseline
    Standalone: Yes
    Depends on scraper scripts: Expects played_backup from util/backup_palyed.py
    Used by scraper scripts: None

util/unplayed_races.py
    Moves played races (except hardcoded done_races URLs) back into races
    Standalone: Yes
    Depends on scraper scripts: None
    Used by scraper scripts: None

races_scraper.log
    Shows output of races_scraper.py and check_races.py
