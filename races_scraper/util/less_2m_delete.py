import os
import sys
from pymongo.errors import BulkWriteError
from pymongo import MongoClient
from dotenv import load_dotenv


# Load .env
load_dotenv("../../.env")

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["horseRacingGame"]
races_collection = db["races"]
races_backup = db["races_backup"]


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


all_races = list(races_collection.find({}))


# Backup all races first
try:
    result = races_backup.insert_many(all_races, ordered=False)
    print(f"Backup complete: {len(result.inserted_ids)} races copied.")
except BulkWriteError as e:
    # Only warn about duplicates, don’t print huge dict
    print(
        "Backup warning: some races already in backup. "
        f"{len(e.details['writeErrors'])} skipped."
    )
except Exception as e:
    print(f"Backup failed: {e}")
    sys.exit(1)

deleted_count = 0
# Will delete all races not 2m or under
for race in all_races:
    if not is_two_miles_or_less(race):
        races_collection.delete_one({"_id": race["_id"]})
        print(f"Deleted race {race['_id']} (distance: {race.get('distance', '?')})")
        deleted_count += 1

new_all_races = list(races_collection.find({}))
new_len = len(new_all_races)
print("")
print(f"Total races deleted: {deleted_count}. Races in dict now: {new_len}")
