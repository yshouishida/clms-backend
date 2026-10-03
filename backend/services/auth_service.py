from werkzeug.security import check_password_hash
from backend.utils.jwt import create_access_token
from backend.utils.jwt_token_blocklist import TOKEN_BLOCKLIST
from backend.repositories.auth_repository import (
    login_repo,
    record_auth_event_repo,
)


def login_service(username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        return None

    username = username.strip()

    if not username or not password:
        return None

    user = login_repo(username)

    if user is None:
        return None

    password_hash = user.get("password_hash")

    if not password_hash:
        return None

    if not check_password_hash(password_hash, password):
        return None

    if user.get("status") != "Active":
        return None

    user.pop("password_hash", None)

    access_token = create_access_token(
        str(user["id"]),
        user["role_name"]
    )

    record_auth_event_repo(
        user_id=user["id"],
        action="LOGIN",
        entity_name="tblUsers",
        record_id=user["id"],
        description="Successful user login.",
        ip_address=ip_address,
    )

    return {
        "access_token": access_token,
        **user
    }

def logout_service(user_id, jti, ip_address=None):
    if user_id is None or not jti:
        return False

    TOKEN_BLOCKLIST.add(jti)

    record_auth_event_repo(
        user_id=user_id,
        action="LOGOUT",
        entity_name="tblUsers",
        record_id=user_id,
        description="User logged out of the CLMS.",
        ip_address=ip_address,
    )

    return True
    
