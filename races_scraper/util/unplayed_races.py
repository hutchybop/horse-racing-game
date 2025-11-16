import os
import sys
from pymongo.errors import DuplicateKeyError
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env
load_dotenv("../../.env")

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["horseRacingGame"]
races_collection = db["races"]
played_races_collection = db["played_races"]

all_played_races = list(played_races_collection.find({}))

done_races = [
    "https://www.racingtv.com/watch/replays/2023-04-16/curragh/1545", 
    "https://www.racingtv.com/watch/replays/2023-05-02/nottingham/1710",
    "https://www.racingtv.com/watch/replays/2023-01-21/navan/1200",
    "https://www.racingtv.com/watch/replays/2023-04-14/leicester/1655",
    "https://www.racingtv.com/watch/replays/2023-01-08/naas/1350",
    "https://www.racingtv.com/watch/replays/2023-04-12/nottingham/1450",
    "https://www.racingtv.com/watch/replays/2023-02-03/dundalk/1830",
    "https://www.racingtv.com/watch/replays/2023-04-27/taunton/1750",
    "https://www.racingtv.com/watch/replays/2023-03-06/leopardstown/1415",
    "https://www.racingtv.com/watch/replays/2023-02-24/dundalk/1830"
]

for race in all_played_races:

    url = race.get("racing_tv_url")   # FIXED key

    if url not in done_races:
        inserted = False

        try:
            races_collection.insert_one(race)
            print(f"Copied race with {url} to races.")
            inserted = True

        except DuplicateKeyError:
            print(f"Race with {url} already exists in races.")
            inserted = True  # safe to delete original

        except Exception as e:
            print(f"Copy failed for {url}: {e}")
            sys.exit(1)

        if inserted:
            played_races_collection.delete_one({"racing_tv_url": url})
