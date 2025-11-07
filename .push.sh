#!/bin/bash

# Ensure correct dir
cd /home/hutch/horse-racing-game

# Pull current changes
git pull

# Change dir
cd /home/hutch/horse-racing-game/get_races

# Run races_scraper.py
/home/hutch/horse-racing-game/get_races/hrg_env/bin/python /home/hutch/horse-racing-game/get_races/races_scraper.py

# Ensure correct dir
cd /home/hutch/horse-racing-game

# Stage all changes
git add -A

# Commit with message
git commit -m "run races_scraper.py"

# Push to current branch
git push

