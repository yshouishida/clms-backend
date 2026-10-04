import os
from dotenv import load_dotenv
import pymysql as mysql
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(
    BACKEND_DIR / ".env",
    encoding="utf-8-sig",
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT")),
    "cursorclass": mysql.cursors.DictCursor
}


def get_connection():
    return mysql.connect(**DB_CONFIG)
