from flask import g, request

from backend.utils.api_response import error, success
from backend.services.auth_service import login_service, logout_service


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

    result = login_service(username, password, request.remote_addr)

    if result is None:
        return error("Invalid username or password.", 401)

    return result, 200


def logout_control():
    logged_out = logout_service(
        user_id=g.user_id,
        jti=g.jti,
        ip_address=request.remote_addr,
    )

    if not logged_out:
        return error("Logout failed.", 500)

    return success("Logged out successfully.", 200)