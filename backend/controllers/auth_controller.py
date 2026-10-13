from flask import g, request

from backend.utils.api_response import error, success
from backend.services.auth_service import login_service, logout_service
from backend.services.laboratory_sessions_service import finish_session_service
from backend.utils.domain_error import DomainError


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

    try:
        result = login_service(username, password, request.remote_addr)
    except Exception:
        return error("Authentication is temporarily unavailable.", 503)

    if result is None:
        return error("Invalid username or password.", 401)

    return result, 200


def logout_control():
    session_id = g.jwt_payload.get("session_id")
    if session_id is not None:
        try:
            finish_session_service(session_id, g.user_id, g.user_role)
        except DomainError as exc:
            return error(str(exc), exc.status_code)
        except Exception:
            return error("Laboratory session logout failed.", 500)

    logged_out = logout_service(
        user_id=g.user_id,
        jti=g.jti,
        ip_address=request.remote_addr,
    )

    if not logged_out:
        return error("Logout failed.", 500)

    return success("Logged out successfully.", 200)
