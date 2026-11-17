"""Local application paths and environment configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"
DATA_DIR = BASE_DIR / "data"
_database_override = os.environ.get("PLACEMENT_DB_PATH", "").strip()
DATABASE_PATH_SOURCE = "PLACEMENT_DB_PATH" if _database_override else "project default"
_database_candidate = Path(_database_override).expanduser() if _database_override else DATA_DIR / "placement_intelligence.sqlite3"
DATABASE_PATH = (_database_candidate if _database_candidate.is_absolute() else BASE_DIR / _database_candidate).resolve()
DATASET_INDEX_PATH = DATA_DIR / "dataset_index.json"
API_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("PLACEMENT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
