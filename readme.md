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
# From which logger level to show - DEBUG < INFO < CHECK < API < SUCCESS < WARNING < ERROR < CRITICAL
LOG_LEVEL=DEBUG || INFO || CHECK || API || SUCCESS || Warning || ERROR || CRITICAL
MONGODB_URI=your_mongodb_connection_string
SECRET_KEY=your_super_secret-_session-key
API_KEY_1=your_rapidapi_key
# ALT_SCRAPER_PATH=path_to_scraper_log_if_required-Optional
```

---

## 🏇 Running the Web App

Start the Flask app on port 3008:

```bash
flask run -p 3008
# or
python3 web.py
```

Visit: [http://localhost:3008](http://localhost:3008)

When the app starts, it now checks whether at least **10 races** exist in the `races`
collection. If not, it redirects to the **Scraper** page where you can run data
collection jobs and monitor live log output.

---

## 🧹 Scraping Races

To populate the database with races:

```bash
python races_scraper/races_scraper.py
```

- Logs are written to: `races_scraper/races_scraper.log`
- Checks for valid **RacingTV replays** before saving races.
- Adheres to RapidAPI terms and conditions.

Note: The initial scrape may take **15–20 minutes** depending on available data.
Note: You may not gain enough races initialy for a full game, meaning you may have to try again when the api limit has been refreshed.

---

## 🧰 Background Job Runner (Docker/Gunicorn Safe)

The app now uses a Mongo-backed job queue for scraper actions:

- `scrape_races` runs `races_scraper/races_scraper.py`
- `move_races` runs `races_scraper/util/move_races.py`
- Job state and logs are stored in MongoDB (`jobs`, `job_logs`)
- A separate worker process executes queued jobs

### Local Development Mode

- If `ENV` is **not** set to `production`, the app auto-starts an in-process job
  worker when running `flask run` or `python3 web.py`.
- This means your existing local `.env` does not need extra worker setup.

### Production Mode

- If `ENV=production`, the web app does **not** auto-start a worker.
- Run the dedicated `worker` process/container for job execution.
- The worker publishes a Mongo heartbeat; container health checks monitor heartbeat freshness.

### Run with Docker Compose

1. Copy `.env.example` to `.env` and set values.
2. For the bundled `mongo` service, set:
   - `MONGODB_URI=mongodb://mongo:27017/horseRacingGame`
3. Start services:

```bash
docker compose up --build
```

Services:

- `web` (Gunicorn Flask app) on `http://localhost:3008`
- `worker` (Mongo-backed job runner)
- `mongo` (MongoDB)

`docker-compose.yml` sets `ENV=production` automatically for `web` and `worker`.

### GHCR image publishing

- Workflow file: `.github/workflows/docker-release.yml`
- Trigger: push of a semver tag like `v0.1.0`
- Guardrail: workflow only publishes if the tagged commit is contained in `main`
- Output image: `ghcr.io/<owner>/<repo>` with `vX.Y.Z`, `latest`, and `sha-...` tags

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
