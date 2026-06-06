import os
from pathlib import Path

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/lecturenote_suite.sqlite3")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
ACTION_API_KEY = os.getenv("ACTION_API_KEY", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
