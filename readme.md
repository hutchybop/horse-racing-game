# 🏇 Horse Racing Game

A fun Flask-based horse racing betting simulation web app that uses real race data scraped from RapidAPI. Bet on horses, watch real RacingTV replays, and see if your picks win!

---

## 🚀 Features

- Real UK/IRE horse races (limited to distances ≤ 2 miles)
- Uses multiple RapidAPI keys for race scraping (with T&Cs compliance)
- Valid RacingTV replays automatically included
- Dynamic race selection with proportional distances
- Play 10 races per session
- Bet returns calculator on results page

---

## 🧰 Setup Instructions

### 1. Create and Activate Python Environment

```bash
python3 -m venv hrg_env
source hrg_env/bin/activate   # macOS/Linux
hrg_env\Scripts\activate    # Windows
```

### 2. Install Requirements

Before installing, open `requirements.txt` and follow any notes to install **Playwright** first (required for scraping).  
Then install dependencies:

```bash
pip3 install -r requirements.txt
```

### 3. Create `.env` File

In the project root, create a `.env` file containing:

```bash
MONGODB_URI=your_mongodb_connection_string
API_KEY_1=your_first_rapidapi_key
API_KEY_2=your_second_key   # Optional
# ... up to API_KEY_10
```

You can add up to **10 RapidAPI keys** to allow for rotation and reduce rate limits.

---

## 🏇 Running the Web App

Start the Flask app (default port 5000):

```bash
flask run
```

Visit: [http://localhost:5000](http://localhost:5000)

---

## 🧹 Scraping Races

To populate the database with races:

```bash
python races_scraper/races_scraper.py
```

- Logs are written to: `races_scraper/races_scraper.log`
- Uses multiple API keys in sequence.
- Checks for valid **RacingTV replays** before saving races.
- Adheres to RapidAPI terms and conditions.

Note: The initial scrape may take **15–20 minutes** depending on available data.

---

## 🕹️ Playing the Game

Once races are in the database (`races` collection):

1. Start the game.
2. View horse info and place your bet.
3. Watch the RacingTV replay.
4. View results and calculate returns.
5. Move on to the next race.

Each game consists of **10 races**, then it ends automatically.

---

## 🧠 Additional Info

- MongoDB is used to store races (`races` collection).  
- A separate collection (`played_races`) is used for race history management.  
- Game logic dynamically selects races based on distance and availability.

---

## ⚠️ Notes

- Always comply with [RapidAPI’s Terms of Use](https://rapidapi.com/terms/).
- Race scraping is for personal and educational use only.
- The game relies on live data availability; occasionally some races may not have valid replays.

---

## 📂 Project Structure

```
horse-racing-game/
│
├── app/                    # Flask web app
│   ├── templates/          # HTML templates
│   ├── static/             # CSS / JS / assets
│   ├── routes.py           # Web routes
│   └── ...
│
├── races_scraper/
│   ├── races_scraper.py    # Scraping script
│   └── races_scraper.log   # Log output
│
├── .env.example            # Example env file (optional)
├── requirements.txt
└── README.md
```

---

## 🏁 License

This project is for educational and entertainment purposes only.  
