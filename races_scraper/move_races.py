import os
from pymongo import MongoClient
from dotenv import load_dotenv

<<<<<<< HEAD
=======
'''Moves races from player_races collection to races collection'''

num_of_races_move = 10

>>>>>>> 606fdcd4ae53300ac0650f62132ae3ebe9819f6a
# --- 1️⃣ Load environment and connect to DB ---
load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["horseRacingGame"]

played_races_collection = db["played_races"]
races_collection = db["races"]

# --- 2️⃣ Transfer 10 documents at a time, with verification ---
<<<<<<< HEAD
def transfer_races(batch_size=10):
=======
def transfer_races(batch_size=20):
>>>>>>> 606fdcd4ae53300ac0650f62132ae3ebe9819f6a
    # Find up to 10 races to transfer
    races_to_move = list(played_races_collection.find().limit(batch_size))

    if not races_to_move:
        print("No races to transfer.")
        return

    # Insert them into the destination collection
    result = races_collection.insert_many(races_to_move)
    inserted_ids = set(result.inserted_ids)

    # --- Verification step ---
    confirmed = races_collection.count_documents({"_id": {"$in": list(inserted_ids)}})
    if confirmed == len(inserted_ids):
        # Only delete if all were confirmed inserted
        played_races_collection.delete_many({"_id": {"$in": list(inserted_ids)}})
        print(f"Successfully transferred and removed {confirmed} races.")
    else:
        print(f"Insert verification failed: expected {len(inserted_ids)}, found {confirmed}. No deletions made.")

if __name__ == "__main__":
<<<<<<< HEAD
    transfer_races()
=======
    transfer_races(num_of_races_move)
>>>>>>> 606fdcd4ae53300ac0650f62132ae3ebe9819f6a
