"""Application configuration using paths relative to this project."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "chatbot.db"


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "development-only-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    PROJECT_ROOT = PROJECT_ROOT
    DATA_DIR = DATA_DIR
    DATABASE_PATH = DATABASE_PATH
