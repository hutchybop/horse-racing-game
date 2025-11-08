import os
import json
import pprint
from collections import Counter
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["horseRacingGame"]
races_collection = db["races"]
race_index_collection = db["race_index"]

# Fetch all races
races = list(races_collection.find({}))

# Prepare Counters
course_counter = Counter()
date_counter = Counter()
distance_counter = Counter()
num_horses_counter = Counter()

# Iterate through races and count values
for race in races:
    course_counter[race.get("course")] += 1
    date_counter[str(race.get("date"))] += 1
    distance_counter[race.get("distance")] += 1
    
    horses = race.get("horses", [])
    num_horses_counter[len(horses)] += 1

# Convert Counters to the requested format
result = {
    "courses": [dict(course_counter)],
    "dates": [dict(date_counter)],
    "distances": [dict(distance_counter)],
    "num_horses": [dict(num_horses_counter)],
}

# Print results nicely
pprint.pprint(result)