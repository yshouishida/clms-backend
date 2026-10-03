from flask import request

from backend.utils.api_response import error
from backend.services.auth_service import login_service


def login_control():
    user_input = request.get_json(silent=True)

    if not isinstance(user_input, dict):
        return error("Request body must be a valid JSON object.", 400)

    username = user_input.get("username")
    password = user_input.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return error("Username and password must be strings.", 400)

    if not username.strip() or not password:
        return error("Username and password are required.", 400)

    result = login_service(username, password)

    if result is None:
        return error("Invalid username or password.", 401)

    return result, 200