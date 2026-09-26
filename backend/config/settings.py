import os

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

JWT_TOKEN_EXPIRES = int(
    os.getenv("JWT_TOKEN_EXPIRES")
)