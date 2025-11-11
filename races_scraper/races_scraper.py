import os
import sys
import requests
import time
import pytz
import logging
from pydantic import BaseModel, HttpUrl, field_validator, ValidationError
from typing import List
from pymongo import MongoClient
from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
    NAME_WIDTH = 4
    # Define the format with alignment
    log_format = f"%(asctime)s - %(filename)s:%(lineno)-{NAME_WIDTH}s - %(levelname)-{LEVEL_WIDTH}s - %(message)s"
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_format = logging.Formatter(log_format)
    console_handler.setFormatter(console_format)
    # File handler
    if os.getenv("location") == "server":
        file_handler = logging.FileHandler(
            "/home/hutch/horse-racing-game/races_scraper/races_scraper.log", mode="a"
        )
    else:
        file_handler = logging.FileHandler("races_scraper.log", mode="a")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(console_format)
    # Attach both
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger



# Exits if .env fails to load API_KEY
def check_api_key():
    # API_KEY setup - simple list
    API_KEYS = [
        os.getenv(f"API_KEY_{i}") 
        for i in range(1, 10) # Increase upperlimit for more keys
    ]
    # Remove None values
    API_KEYS = [key for key in API_KEYS if key]  

    if not API_KEYS:
        logger.critical("No API keys found! Set API_KEY_1, API_KEY_2, etc. Exiting")
        raise SystemExit(1)
    else:
        return API_KEYS


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


# Setting up Mongo DB models
class Horse(BaseModel):
    name: str
    age: str
    weight: str
    number: str
    form: str
    sp: str
    last_ran_days_ago: str
    position: str

class Race(BaseModel):
    title: str
    course: str
    date: str
    distance: str
    horses: List[Horse]
    racing_tv_url: HttpUrl

    # Check required text fields are not empty
    @field_validator("title", "course", "date", "distance", "racing_tv_url")
    def no_empty_fields(cls, v):
        if not v or str(v).strip() == "":
            raise ValueError("Field cannot be empty")
        return v

    # Ensure horse count between 2 and 8
    @field_validator("horses")
    def valid_horse_count(cls, v):
        if not (2 <= len(v) <= 8):
            raise ValueError("Each race must have between 2 and 8 horses")
        return v


class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    def __init__(self, reset_time, api_calls, message="Rate limit reached"):
        self.reset_time = reset_time
        self.api_calls = api_calls
        self.message = message
        super().__init__(self.message)


def get_api_data(endpoint, param_type=None, param=None, current_key_index=0):
    """
    Fetch data from the RapidAPI Horse Racing API.
    Args:
        endpoint (str): "race" or "racecards".
        param_type (str, optional): Query type like "date".
        param (str, optional): Race ID or date string.
    Returns:
        tuple: (data, api_calls)
    Raises:
        RateLimitError: When rate limit is exceeded after retries
        ValueError: For invalid endpoints
        requests.exceptions.RequestException: For other HTTP or connection errors
    """
    # Build URL based on endpoint type
    base_url = "https://horse-racing.p.rapidapi.com"
    if endpoint == "race":
        rapidapi_url = f"{base_url}/race/{param}"
        params = None
    elif endpoint == "racecards":
        rapidapi_url = f"{base_url}/racecards"
        params = {param_type: param}
    else:
        raise ValueError(f"Unknown endpoint: {endpoint}")
    
    API_KEY = API_KEYS[current_key_index]

    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "horse-racing.p.rapidapi.com"
    }
    # Retry logic
    max_retries = 1
    retry_delay = 30  # seconds
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(rapidapi_url, headers=headers, params=params)
            response.raise_for_status()
            api_calls = int(response.headers.get("X-RateLimit-Requests-Remaining", 0))
            logger.debug("get_api_data() response.headers")
            logger.debug(response.headers)
            return response.json(), api_calls
        except requests.exceptions.HTTPError:
            status = response.status_code
            logger.debug("get_api_data() response.headers")
            logger.debug(response.headers)
            api_calls = int(response.headers.get("X-RateLimit-Requests-Remaining", 0))
            api_reset_seconds = int(response.headers.get("X-RateLimit-Requests-Reset", 0) or 0)
            if status == 429:
                # Calculate reset time
                london_tz = pytz.timezone("Europe/London")
                now_london = datetime.now(london_tz)
                reset_time_london = now_london + timedelta(seconds=api_reset_seconds)
                if api_calls == 0:
                    raise RateLimitError(
                        reset_time=reset_time_london.strftime("%Y-%m-%d %H:%M:%S"),
                        api_calls=api_calls,
                        message="Hard rate limit reached — saving progress and exiting safely."
                    )
                if attempt < max_retries:
                    logger.warning(f"Rate limit hit (429). Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise RateLimitError(
                        reset_time=reset_time_london.strftime("%Y-%m-%d %H:%M:%S"),
                        api_calls=api_calls,
                        message="Rate limit reached after retring — exiting safely."
                    )
        except Exception:
            raise


def get_racingtv_courses(date, page):
    """
    Scrape Racing TV for available course names on a given date.
    Args:
        date (str): Date in "YYYY-MM-DD" format.
        page (playwright.Page): Playwright page instance.
    Returns:
        list[str]: Unique lowercase course names.
    """
    racingtv_url = f"https://www.racingtv.com/watch/replays/{date}"
    courses = []
    try:
        # Clear cookies and cache between navigations
        context.clear_cookies()
        # Optional: set a consistent viewport
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(racingtv_url, timeout=20000)
        # Wait up to 5 seconds for the course divs
        page.wait_for_selector("div.css-146c3p1.r-zso239", timeout=5000)
        # Grab all course divs
        course_divs = page.query_selector_all("div.css-146c3p1.r-zso239")
        for div in course_divs:
            text = div.text_content().strip().lower()
            # Allow multi-word course names
            if all(c.isalpha() or c.isspace() for c in text):
                courses.append(text)
    except TimeoutError:
        logger.info(f"No races found on {date}")
        courses = []
    # Remove duplicates
    return list(set(courses))


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
        logger.error(f"Invalid date format for race {race_data.get('id_race')}")
        return False, "#"
    # Format date and time parts
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H%M")
    # Format course for URL (lowercase, hyphens instead of spaces)
    course_slug = course.lower().replace(" ", "-")
    # Build the final URL
    racingtv_url = f"https://www.racingtv.com/watch/replays/{date_str}/{course_slug}/{time_str}"
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
            # Check for a valid video element with a 'poster' attribute (only present on working videos)
            video_element = page.query_selector("video[poster]")
            if video_element:
                return True, racingtv_url
            # If no poster but also no error text, retry once more
            logger.warning(f"Attempt {attempt + 1}: uncertain result, retrying...")
            time.sleep(2)
        except TimeoutError:
            logger.warning(f"Attempt {attempt + 1}: timeout fetching video page, retrying...")
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
    num_horses = 0
    for h in race_data.get("horses", []):
        non_runner = h.get("non_runner")
        if non_runner == "0":
            num_horses += 1
    # Check if number of horses is between 2 and 8
    valid_num_horses = 2 <= num_horses <= 8
    return valid_num_horses, num_horses

def is_two_miles_or_less(race_data):
    """
    Returns True if distance <= 2 miles (16 furlongs), otherwise False.
    Handles formats like '5f', '1m4f', '2m', '1m7f', etc.
    """
    miles = 0
    furlongs = 0
    for distance_str in race_data.get("distance", "0"):
        # Parse the string
        if 'm' in distance_str:
            parts = distance_str.split('m')
            miles = int(parts[0]) if parts[0] else 0
            if 'f' in parts[1]:
                furlongs = int(parts[1].replace('f', ''))
        elif 'f' in distance_str:
            furlongs = int(distance_str.replace('f', ''))

        total_furlongs = miles * 8 + furlongs
        return total_furlongs <= 16


def build_races_dict(race_data, racingtv_url):
    """
    Build and validate a race dictionary from parsed data.
    Args:
        race_data (dict): Raw race data containing race and horse details.
        racingtv_url (str): URL for the Racing TV race page.
    Returns:
        tuple: (bool, dict) — True and race dict if valid, else False and empty dict.
    """
    # Build race dict
    race = {
        "title": race_data.get("title", ""),
        "course": race_data.get("course", ""),
        "date": race_data.get("date", ""),
        "distance": race_data.get("distance", ""),
        "horses": [
            {
                "name": horse.get("horse", ""),
                "age": horse.get("age", ""),
                "weight": horse.get("weight", ""),
                "number": horse.get("number", ""),
                "form": horse.get("form", ""),
                "sp": horse.get("sp", ""),
                "last_ran_days_ago": horse.get("last_ran_days_ago", ""),
                "position": horse.get("position", "")
            }
            for horse in race_data.get("horses", [])
            if horse.get("non_runner") == "0"  # Only include runners (non-runners = 0)
        ],
        "racing_tv_url": racingtv_url
    }
    # Validate race and horses with pydantic
    try:
        validated_data = Race(**race)
        return True, race
    except ValidationError as e:
        return False, {}


# Main script
if __name__ == "__main__":

    # Setup
    logger = setup_logger()
    API_KEYS = check_api_key()
    races_collection, race_index_collection = mongodb_connection()
    
    # Limits
    max_days_to_try = 10
    days_checked = 0
    current_key_index = 0

    # Launch browser once for all checks
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        logger.info("")
        logger.info("")
        logger.info("$" * 60)
        logger.info("File: races_scraper.py")
        logger.info("Scraping rapidapi.com for race data")
        logger.info("$" * 60)

        logger.info("Initial setup Complete")


        try:

            while days_checked < max_days_to_try:

                # get the race_ids doc from db. (should only ever be one doc)
                race_index = race_index_collection.find_one()


                # --------------------------------------Process Race IDs--------------------------------------
                logger.info("=" * 60)
                logger.info("Processing Race IDs")
                logger.info("=" * 60)
                
                if "race_ids" in race_index and race_index["race_ids"]:

                    num_of_race_ids = len(race_index.get("race_ids", []))
                    logger.info(f"Number of Race IDs to check {num_of_race_ids}")

                    ids_added = 0
                    
                    # Create a copy of races_ids and loop through
                    for race_id in race_index.get("race_ids", [])[:]:
                    
                        logger.check(f"Checking race ID: {race_id}")

                        api_calls = None # initialise api_calls, stops old data being shown
        
                        try:
                            race_data, api_calls = get_api_data(endpoint="race", param=race_id, current_key_index=current_key_index)
                            logger.api(f"API Requests Remaining: {api_calls}, waiting 6 seconds")
                            time.sleep(6)
                        except RateLimitError as e:
                            current_key_index += 1
                            if current_key_index < len(API_KEYS):
                                logger.api(f"Rate limit reached for API_KEY_{current_key_index}")
                                logger.api(f"API Requests left for Key: {e.api_calls}")
                                logger.api(f"API key will reset at: {e.reset_time}")
                                logger.warning("Trying next key, if there is one...")
                                continue
                            logger.api(f"API Requests left for Key: {e.api_calls}")
                            logger.api(f"API key will reset at: {e.reset_time}")
                            logger.critical(e.message)
                            raise SystemExit(1)
                        except Exception as e:
                            logger.error(f"Unexpected error processing race {race_id}: {e}")
                            logger.warning(f"Skipping race race id {race_id} due to error")
                            if api_calls is not None:
                                logger.api(f"API Requests left for Key: {api_calls}")
                            # Remove race_id from race_ids list in db
                            race_index_collection.update_one({}, {"$pull": {"race_ids": race_id}})
                            time.sleep(6)
                            continue
        
                        # Checking valid number of horses and Racing TV link
                        valid_racingtv, racingtv_url = is_valid_racingtv_url(race_data, page)
                        valid_num_horses, num_horses = is_correct_num_horses(race_data)
                        valid_distance = is_two_miles_or_less(race_data)
                        valid_race, race = build_races_dict(race_data, racingtv_url) # checks all values are present in dict
        
                        if valid_racingtv and valid_num_horses and valid_distance and valid_race:
                            # Add race to races collection in db
                            races_collection.insert_one(race)
                            ids_added += 1
                            # Remove race_id from race_ids list in db
                            race_index_collection.update_one({}, {"$pull": {"race_ids": race_id}})
                            logger.success(f"{race_id} added to races collection in db")
                            #  Get number of races in db
                            race_count = races_collection.count_documents({})
                            logger.info(f"Total races added to DB so far: {race_count}")
                        else:
                            # Show error if race not valid
                            if not valid_racingtv:
                                logger.warning(f"No valid Racing TV Video, race id {race_id} not added")
                            if not valid_num_horses:
                                if num_horses < 2:
                                    logger.warning(f"Not enough horses ran, race id {race_id} not added")
                                if num_horses > 8:
                                    logger.warning(f"Too many horses ran, race id {race_id} not added")
                            if not valid_distance:
                                logger.warning(f"Race distance too long, race id {race_id} not added")
                            if not valid_race:
                                logger.warning(f"{race_id} skipped (missing fields or invalid horses)")

                            # Remove race_id
                            race_index_collection.update_one({}, {"$pull": {"race_ids": race_id}})
                    
                    # Logs after loop has finished
                    logger.info(f"Out of {num_of_race_ids} Race IDs, {ids_added} added to db")
                    logger.info("No more Race IDs to process, indexing Race IDs for next day")
                
                else:
                    logger.info("No racing IDs to process, indexing Race IDs for next day")

                logger.info("")  # logs an empty line

                # --------------------------------------Index Race IDs for the Next Date--------------------------------------
                # Get the date to check
                last_race_date = race_index.get("current_race_date", "2022-12-31")
                # Convert to datetime, add one day, and convert back to string
                race_date = (datetime.strptime(last_race_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                
                logger.info("=" * 60)
                logger.info(f"Indexing Race IDs for {race_date}")
                logger.info("=" * 60)
                
                # Check vlaid course for the date
                valid_courses = get_racingtv_courses(race_date, page)

                logger.info(f"Getting Race IDs for {race_date}")

                api_calls = None

                # Get racecard api data
                try:
                    race_card_data, api_calls = get_api_data(endpoint="racecards", param_type="date", param=race_date, current_key_index=current_key_index)
                    days_checked = 0
                    logger.api(f"API Requests Remaining: {api_calls}, waiting 6 seconds")
                    time.sleep(6)
                except RateLimitError as e:
                    current_key_index += 1
                    if current_key_index < len(API_KEYS):
                        logger.api(f"Rate limit reached for API_KEY_{current_key_index}")
                        logger.api(f"API Requests left for Key: {e.api_calls}")
                        logger.api(f"API key will reset at: {e.reset_time}")
                        logger.warning("Trying next key, if there is one...")
                        continue
                    logger.api(f"API Requests left for Key: {e.api_calls}")
                    logger.api(f"API key will reset at: {e.reset_time}")
                    logger.critical(e.message)
                    raise SystemExit(1)
                except Exception as e:
                    logger.error(f"Unexpected error processing race date {race_date}: {e}")
                    logger.warning(f"Skipping race date {race_date} due to error")
                    if api_calls is not None:
                        logger.api(f"API Requests left for Key: {api_calls}")
                    days_checked += 1
                    time.sleep(6)
                    continue

                # Checks racecard courses against valid courses and adds race_id to race_ids if valid
                num_of_races_added = 0
                for race in race_card_data:
                    race_course = race.get("course", "")
                    race_course_slug = race_course.lower().replace(" ", "-")
                    if race_course_slug in valid_courses:
                        id_race = race.get("id_race")
                        # Add race_id to race_ids list in db, only if not already present
                        race_index_collection.update_one({}, {"$addToSet": {"race_ids": id_race}})
                        num_of_races_added += 1

                # Update the current_race_date so the script continues from next date next time
                race_index_collection.update_one({}, {"$set": {"current_race_date": race_date}})

                num_of_races_in_RCD = len(race_card_data)

                logger.info(f"Out of {num_of_races_in_RCD} races, {num_of_races_added} added to race_index")
                logger.info(f"All valid Race IDs for {race_date} added, now processing Race IDs")

                logger.info("")  # logs an empty line


        except KeyboardInterrupt:
            logger.warning("Manual stop detected. Cleaning up...")
            raise SystemExit(0)
        except Exception as e:
            logger.error(f"Unexpected crash: {e}")
        finally:
            try:
                race_count = races_collection.count_documents({})

                if browser.is_connected():
                    browser.close()
                    logger.info("Browser closed cleanly")

                logger.info(f"Total amount of Races currently in DB: {race_count}")
                logger.info("Cleanup complete")
                logger.info("")

            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
                logger.info("")
            
