import os
from dotenv import load_dotenv
import pymysql as mysql


load_dotenv()

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
