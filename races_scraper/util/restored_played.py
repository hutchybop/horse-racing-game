import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env
load_dotenv("../../.env")

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["horseRacingGame"]

played = db["played_races"]
backup = db["played_backup"]
races = db["races"]

# Create a set of all original backup IDs
backup_ids = {doc["_id"] for doc in backup.find({})}

# Iterate through current played_races
for race in played.find({}):
    race_id = race["_id"]

    # If NOT in original backup → this was added later → move back to races
    if race_id not in backup_ids:
        races.insert_one(race)
        played.delete_one({"_id": race_id})
