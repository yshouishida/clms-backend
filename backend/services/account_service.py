from werkzeug.security import generate_password_hash

from backend.repositories.account_repository import (
    get_admins_repo, create_admin_repo, update_admin_repo, set_account_status_repo,
)
from backend.services.rfid_service import positive_id
from backend.utils.domain_error import DomainError


def get_admins_service():
    return get_admins_repo()


def create_admin_service(body):
    values = _validate_admin_fields(body)
    password = body.get("password")

    if not isinstance(password, str) or len(password) < 8:
        raise DomainError("password must be at least 8 characters.")

    return create_admin_repo(values, generate_password_hash(password))


def _validate_admin_fields(body):
    limits = {
        "account_id": 30,
        "first_name": 50,
        "last_name": 50,
        "email": 100,
        "username": 50
    }
    values = {}

    for field, limit in limits.items():
        value = body.get(field)

        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
            raise DomainError(f"{field} must be a nonempty string of at most {limit} characters.")

        values[field] = value.strip()

    return values


def update_admin_service(user_id, body):
    positive_id(user_id, "user_id")
    values = _validate_admin_fields(body)
    password = body.get("password")

    if password is not None and (not isinstance(password, str) or len(password) < 8):
        raise DomainError("password must be at least 8 characters.")

    return update_admin_repo(
        user_id,
        values,
        generate_password_hash(password) if password is not None else None
    )


def set_account_status_service(user_id, status, actor_user_id):
    positive_id(user_id, "user_id")

    if status not in ("Active", "Disabled"):
        raise DomainError("status must be Active or Disabled.")
    if status == "Disabled" and user_id == actor_user_id:
        raise DomainError("Administrators cannot disable their own account.", 409)

    return set_account_status_repo(user_id, status)
