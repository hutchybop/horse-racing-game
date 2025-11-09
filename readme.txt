# ---------------Usage---------------

Make sure python env is set:
    source <env name>/bin/activate

Make sure .env has correct keys - see below

Check Mongodb horseRacingGame:
    races - has 10 or more races
    If not, run:
        races_scraper/races_scraper.py
        Should be able to scrape enough races, might take 15-20 mins
        If fails and races in played_races run: 
            races_scraper/move_races.py

Run flask (from root):
    flask run
    http://127.0.0.1:5000/


# ---------- Initial setup ----------

Create python enviroment and enable:
    change directory to project root
    python3 -m venv hrg_env
    source <env name>/bin/activate

Install required packages:
    pip3 install --upgrade pip setuptools wheel
    pip3 install -r requirements.txt

Install playwright (for server look at requirements.txt):
    python -m playwright install

Setup .env:
    create .env in project root if not already there.
    Add:
        location="server" # only applicable for the server, allows logger to save to races_scraper.log
        MONGODB_URI # for horceRacingGame db
        API_KEY_1 # from rapidapi.com - horse racing - multiple keys allowed


# ---------- Mongodb horseRacinGame DB config ----------

races
    Holds race dicts used for the game
    Scraped using races_scraper.py

races_index 
    Holds race ids from rapidapi and the last date to be scraped
    Used to scrape races for races

game_races
    Holds 10 races and game tracker for game
    Populated from races by web app

played_races
    Holds all races already played_races
    Can run move_races.py to move 10 back over to races


# ----------------- Scripts and logs -----------------

races_scraper.py
    Will get races from rapidapi.com
    Checks:
        racing tv video is avaiable
        number of horses is between 2-8 - ensure all data fits on screen
        race distance is 2m or under - stops long race times on replay
        checks all race fields are present

move_races.py
    Moves old races from payed_races to races
    Default is 10 - can be changed in fields
    Allows old races to be used if scraper fails

races_scraper.log
    Shows output of races_scraper.py

