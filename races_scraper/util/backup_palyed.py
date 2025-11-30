import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env
load_dotenv("../../.env")

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["horseRacingGame"]
played_races_collection = db["played_races"]
played_backup_collection = db["played_backup"]

all_played_races = list(played_races_collection.find({}))

played_backup_collection.insert_many(all_played_races)
