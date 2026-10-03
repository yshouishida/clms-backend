import jwt
import uuid
from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, g
from backend.utils.api_response import error
from backend.utils.jwt_token_blocklist import TOKEN_BLOCKLIST
from backend.config.settings import (
    JWT_SECRET_KEY, 
    JWT_ACCESS_TOKEN_EXPIRES
)


def create_access_token(identity, role):
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(identity),
        "jti": jti,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES),
        "role": role
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token


def token_required(f):
    @wraps(f)

    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return error("Authorization is required.", 401)
        token = auth_header.split("")[1]

        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            jti  = payload.get("jti")

            if jti in TOKEN_BLOCKLIST:
                return error("Token has been revoked.", 401)

            g.jti = jti
            g.user_id = int(payload.get("sub"))
            g.user_role = payload.get("role")
            g.jwt_payload = payload

            
        except jwt.ExpiredSignatureError:
            return error("Token has been expired. Please login again.", 401)
        
        except jwt.InvalidTokenError:
            return error("Invalid token.", 401)

        return f(*args, **kwargs)

    return decorated


def role_required(role_required):
    def decorator(f):
        @wraps(f)

        def decorated(*args, **kwargs):
            user_role = g.user_role

            if user_role.lower() != role_required.lower():
                return error(f"Access denied. {role_required} is required role", 401)

            return f(*args, **kwargs)

        return decorated

    return decorator

            
            



