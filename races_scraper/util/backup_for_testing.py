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

KEEP_RACES = 5


def backup_races_for_testing(keep_count=KEEP_RACES):
    total_races = races_collection.count_documents({})

    if total_races <= keep_count:
        print(
            f"No backup needed. races has {total_races} docs "
            f"(<= keep target {keep_count})."
        )
        return

    keep_docs = list(
        races_collection.find({}, {"_id": 1}).sort("_id", -1).limit(keep_count)
    )
    keep_ids = [doc["_id"] for doc in keep_docs]

    move_cursor = races_collection.find({"_id": {"$nin": keep_ids}})

    moved_ids = []
    moved_count = 0
    for race in move_cursor:
        backup_collection.replace_one({"_id": race["_id"]}, race, upsert=True)
        moved_ids.append(race["_id"])
        moved_count += 1

    if moved_ids:
        races_collection.delete_many({"_id": {"$in": moved_ids}})

    print(
        f"Moved {moved_count} races to races_backup_testing. "
        f"races now has {races_collection.count_documents({})} docs."
    )


if __name__ == "__main__":
    backup_races_for_testing()
