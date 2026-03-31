import os
import sys
import time
import logging
import json
from pymongo import MongoClient
from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
from datetime import datetime

# Load .env
load_dotenv("../.env")


# Logger setup
# In order: DEBUG < INFO < CHECK < API < SUUCCESS < WARNING < ERROR < CRITICAL
def setup_logger():
    """Setup logger with console + file output, and custom log levels."""
    # Define custom levels
    CHECK_LEVEL = 22
    API_LEVEL = 25
    SUCCESS_LEVEL = 28
    logging.addLevelName(CHECK_LEVEL, "CHECK")
    logging.addLevelName(API_LEVEL, "API")
    logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

    def check(self, message, *args, **kwargs):
        if self.isEnabledFor(CHECK_LEVEL):
            self._log(CHECK_LEVEL, message, args, **kwargs)

    def api(self, message, *args, **kwargs):
        if self.isEnabledFor(API_LEVEL):
            self._log(API_LEVEL, message, args, **kwargs)

    def success(self, message, *args, **kwargs):
        if self.isEnabledFor(SUCCESS_LEVEL):
            self._log(SUCCESS_LEVEL, message, args, **kwargs)

    logging.Logger.check = check
    logging.Logger.api = api
    logging.Logger.success = success
    # Setup base logger
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    logger = logging.getLogger("races_scraper")
    logger.setLevel(numeric_level)
    logger.handlers.clear()  # Ensure no duplicate handlers on reload
    # Define consistent width for log level column
    LEVEL_WIDTH = 9  # Long enough to fit the longest level name (e.g., "WARNING")
    NAME_WIDTH = 6
    # Define the format with alignment
    log_format = (
        "%(asctime)s - %(filename)s:%(lineno)-"
        f"{NAME_WIDTH}s - %(levelname)-"
        f"{LEVEL_WIDTH}s - %(message)s"
    )
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_format = logging.Formatter(log_format)
    console_handler.setFormatter(console_format)
    # File handler
    log_path = os.getenv("ALT_SCRAPER_PATH", "races_scraper.log")
    file_handler = logging.FileHandler(log_path, mode="a")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(console_format)
    # Attach both
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


# Connect to MongoDB
def mongodb_connection():
    try:
        client = MongoClient(os.getenv("MONGODB_URI"))
        db = client["horseRacingGame"]
        races_collection = db["races"]
        race_index_collection = db["race_index"]
        return races_collection, race_index_collection
    except Exception as e:
        logger.critical(f"There has been a DB error: {e}")
        logger.critical("Exiting...")
        raise SystemExit(1)


def is_valid_racingtv_url(race_data, page):
    """
    Check if a Racing TV replay URL is valid and playable.
    Args:
        race_data (dict): Contains course and date info.
        page (playwright.Page): Playwright page for navigation.
    Returns:
        tuple[bool, str]: (is_valid, replay_url)
    """
    # Get course and date info
    course = race_data.get("course")
    race_date = race_data.get("date")
    try:
        # Parse the race_date into a datetime object
        dt = datetime.strptime(race_date, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        print()
        logger.error(f"Invalid date format for race {race_data.get('id_race')}")
        return False, "#"
    # Format date and time parts
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H%M")
    # Format course for URL (lowercase, hyphens instead of spaces)
    course_slug = course.lower().replace(" ", "-")
    # Build the final URL
    racingtv_url = (
        f"https://www.racingtv.com/watch/replays/{date_str}/{course_slug}/{time_str}"
    )
    # Retry logic
    retries = 3
    for attempt in range(retries):
        try:
            # Clear cookies and cache between navigations
            context.clear_cookies()
            # Optional: set a consistent viewport
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.goto(racingtv_url, timeout=20000)
            # If "Cannot find this race" text appears → invalid
            if page.query_selector("text=Cannot find this race"):
                return False, "#"
            # Check for a valid video element with a 'poster' attribute
            # (only present on working videos)
            video_element = page.query_selector("video[poster]")
            if video_element:
                return True, racingtv_url
            # If no poster but also no error text, retry once more
            print()
            logger.debug(f"Attempt {attempt + 1}: uncertain result, retrying...")
            time.sleep(2)
        except TimeoutError:
            print()
            logger.debug(
                f"Attempt {attempt + 1}: timeout fetching video page, retrying..."
            )
            time.sleep(2)
    return False, "#"  # After all retries failed


def is_correct_num_horses(race_data):
    """
    Validate if race has between 2 & 8 runners.
    Args:
        race_data (dict): Race data including "horses" list.
    Returns:
        tuple[bool, int]: (is_valid, num_horses)
    """
    # Get number of horses that ran
    horses = race_data.get("horses")
    num_horses = len(horses)
    # Check if number of horses is between 2 and 8
    valid_num_horses = 2 <= num_horses <= 8
    return valid_num_horses, num_horses


def is_two_miles_or_less(race_data):
    distance_str = race_data.get("distance", "").replace(" ", "").lower()

    miles = 0
    furlongs = 0

    # Case: distance like "3m", "3m2f", "2m4f"
    if "m" in distance_str:
        parts = distance_str.split("m")
        miles = int(parts[0]) if parts[0] else 0
        if parts[1].endswith("f"):
            furlongs = int(parts[1].replace("f", ""))

    # Case: only furlongs like "5f"
    elif distance_str.endswith("f"):
        furlongs = int(distance_str.replace("f", ""))

    total_furlongs = miles * 8 + furlongs
    return total_furlongs <= 16


def valid_race_values(race_data):
    """
    Check every field in a race dict (including nested horse dicts)
    for missing or invalid values, except 'form' and 'last_ran_days_ago'
    inside horse dicts.
    Returns:
        (True, []) if all valid
        (False, [list of invalid key paths]) otherwise
    """
    invalid_values = {None, "", " ", "null", "None"}
    invalid_keys = []

    def check_value(value, path, parent_key=None):
        if isinstance(value, dict):
            skip_keys = (
                {"form", "last_ran_days_ago"} if parent_key == "horses" else set()
            )
            for k, v in value.items():
                if k in skip_keys:
                    continue
                check_value(v, f"{path}.{k}" if path else k, parent_key=k)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                # If this list is under 'horses', we pass parent_key='horses'
                check_value(item, f"{path}[{i}]", parent_key=parent_key)
        else:
            if isinstance(value, str):
                if value.strip() == "" or value in invalid_values:
                    invalid_keys.append(path)
            elif value in invalid_values:
                invalid_keys.append(path)

    check_value(race_data, "", parent_key=None)
    if invalid_keys:
        return False, invalid_keys
    return True, []


# Main script
if __name__ == "__main__":

    # Setup
    races_collection, race_index_collection = mongodb_connection()
    logger = setup_logger()
    invalid_races = {}

    # Get all races from races
    races = list(races_collection.find())
    races_length = len(races)

    # Launch browser once for all checks
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        logger.info("")
        logger.info("$" * 60)
        logger.info("File: check_races.py")
        logger.info("Carrying out validation checks on all races")
        logger.info("$" * 60)
        logger.debug("Initial setup complete")

        try:

            for i, race_data in enumerate(races, start=1):
                # Progress printed in-place on one line
                sys.stdout.write(
                    f"\rRace {i} of {races_length} ({(i / races_length) * 100:.1f}%)"
                )
                sys.stdout.flush()

                race_id = race_data.get("_id", "")
                invalid_race = {}

                valid_racingtv, racingtv_url = is_valid_racingtv_url(race_data, page)
                valid_num_horses, num_horses = is_correct_num_horses(race_data)
                valid_distance = is_two_miles_or_less(race_data)
                valid_values, error_values = valid_race_values(race_data)

                if not valid_racingtv:
                    invalid_race["invalid_racingTV_url"] = race_data.get(
                        "racing_tv_url", ""
                    )
                if not valid_num_horses:
                    invalid_race["invalid_num_of_horses"] = num_horses
                if not valid_distance:
                    invalid_race["invalid_distance"] = race_data.get("distance", "")
                if not valid_values:
                    invalid_race["invalid_values"] = error_values

                if invalid_race:
                    invalid_races[race_id] = invalid_race
                    print()
                    print(invalid_race)

            # Move to a new line once loop finishes
            print()
            if invalid_races:
                logger.info(
                    "Some races failed checks:\n%s", json.dumps(invalid_races, indent=4)
                )
            else:
                logger.info("All races checked, all good!!")

        except KeyboardInterrupt:
            print("Manual stop detected. Cleaning up...")
            if browser.is_connected():
                browser.close()
            raise SystemExit(0)
        except Exception as e:
            print(f"Unexpected crash: {e}")
        finally:
            try:
                if browser.is_connected():
                    browser.close()
                    print("Browser closed cleanly")

                print("Cleanup complete\n")

            except Exception as e:
                print(f"Error closing browser: {e}")
                print("")
