import jwt
import uuid
from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, g
from backend.utils.api_response import error
from backend.utils.domain_error import DomainError
from backend.utils.jwt_token_blocklist import TOKEN_BLOCKLIST
from backend.repositories.auth_repository import get_auth_identity_repo
from backend.config.settings import (
    JWT_SECRET_KEY,
    JWT_ACCESS_TOKEN_EXPIRES
)


def validate_jwt_configuration():
    if not isinstance(JWT_SECRET_KEY, str) or len(JWT_SECRET_KEY) < 32:
        raise DomainError("Authentication is temporarily unavailable.", 503)


def create_access_token(identity, role, session_id=None):
    validate_jwt_configuration()
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(identity),
        "jti": jti,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES),
        "role": role
    }
    if session_id is not None:
        payload["session_id"] = session_id
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token


def token_required(f):
    @wraps(f)

    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return error("Authorization is required.", 401)
        token = auth_header[7:].strip()

        try:
            validate_jwt_configuration()
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "jti", "role"]}
            )
            jti = payload.get("jti")

            if not isinstance(jti, str) or not jti or jti in TOKEN_BLOCKLIST:
                return error("Token has been revoked.", 401)

            g.jti = jti
            g.user_id = int(payload.get("sub"))
            if g.user_id < 1:
                return error("Invalid token.", 401)
            identity = get_auth_identity_repo(g.user_id)
            if not identity or identity["status"] != "Active":
                return error("Account is not active.", 401)
            if identity["role_name"] != payload.get("role"):
                return error("Token role is no longer valid.", 401)
            g.user_role = identity["role_name"]
            g.jwt_payload = payload


        except jwt.ExpiredSignatureError:
            return error("Token has been expired. Please login again.", 401)

        except (jwt.InvalidTokenError, TypeError, ValueError):
            return error("Invalid token.", 401)

        except Exception:
            return error("Authentication is temporarily unavailable.", 503)

        return f(*args, **kwargs)

    return decorated



def role_required(*allowed_roles):
    normalized_roles = {
        role.lower() for role in allowed_roles
    }

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = getattr(g, "user_role", None)

            if not isinstance(user_role, str):
                return error("Authentication is required.", 401)

            if user_role.lower() not in normalized_roles:
                required_roles = " or ".join(allowed_roles)

                return error(
                    f"Access denied. Required role: {required_roles}.",
                    403
                )

            return f(*args, **kwargs)

        return decorated

    return decorator






