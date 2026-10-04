import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(
    BACKEND_DIR / ".env",
    encoding="utf-8-sig",
)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

JWT_ACCESS_TOKEN_EXPIRES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRES")
)