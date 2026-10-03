from werkzeug.security import check_password_hash
from backend.utils.jwt import create_access_token
from backend.repositories.auth_repository import login_repo


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

    return {
        "access_token": access_token,
        **user
    }