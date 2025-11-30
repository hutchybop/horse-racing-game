import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv

from controllers.race_control import race_control

load_dotenv()


def create_app():

    app = Flask(__name__)

    # Mongo setup
    app.config["MONGODB_URI"] = os.environ.get("MONGODB_URI")
    app.db = MongoClient(app.config["MONGODB_URI"]).get_default_database()

    # app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["SECRET_KEY"] = "devsecret"

    app.config["TEMPLATES_AUTO_RELOAD"] = True  # auto reloads templates on edit

    app.register_blueprint(race_control)

    return app
