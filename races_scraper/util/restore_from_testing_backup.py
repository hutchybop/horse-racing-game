import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

mongodb_uri = os.getenv("MONGODB_URI")
if not mongodb_uri:
    raise SystemExit(
        f"MONGODB_URI is not set. Add it to {ENV_PATH} or export it in your shell."
    )

client = MongoClient(mongodb_uri)
db = client["horseRacingGame"]
races_collection = db["races"]
backup_collection = db["races_backup_testing"]


def restore_races_from_backup():
    backup_races = list(backup_collection.find({}))
    if not backup_races:
        print("No races found in races_backup_testing.")
        return

    restored_ids = []
    for race in backup_races:
        races_collection.replace_one({"_id": race["_id"]}, race, upsert=True)
        restored_ids.append(race["_id"])

    backup_collection.delete_many({"_id": {"$in": restored_ids}})

    print(
        f"Restored {len(restored_ids)} races into races and "
        f"cleared them from races_backup_testing."
    )


if __name__ == "__main__":
    restore_races_from_backup()
