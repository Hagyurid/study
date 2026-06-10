import os
from pathlib import Path

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/lecturenote_suite.sqlite3")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
ACTION_API_KEY = os.getenv("ACTION_API_KEY", "")

def _normalize_public_base_url(value: str) -> str:
    base = (value or "https://study-xqe8.onrender.com").strip().rstrip("/")
    # Historical typo guard: xge8 must never leak into Action URLs.
    base = base.replace("study-xge8.onrender.com", "study-xqe8.onrender.com")
    return base or "https://study-xqe8.onrender.com"

PUBLIC_BASE_URL = _normalize_public_base_url(os.getenv("PUBLIC_BASE_URL", "https://study-xqe8.onrender.com"))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
