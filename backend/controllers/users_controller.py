from backend.utils.api_response import success, error
from flask import g, request
from pymysql.err import IntegrityError
from backend.services.account_service import (
    get_admins_service, create_admin_service, update_admin_service,
    set_account_status_service,
)
from backend.utils.domain_error import DomainError
from backend.services.users_service import (
    get_users_service,
    get_user_by_id_service
)

def get_users_control():
    users = get_users_service()

    if users is None:
        return error("Users are not found.", 404)

    return success("Get successfully.", 200, users)

def get_user_by_id_control(id):
    user = get_user_by_id_service(id, g.user_role == "Admin")

    if user is None:
        return error("User is not found.", 404)

    return success("Get successfully.", 200, user)


def create_admin_control():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    try:
        result = create_admin_service(body)
        return success("Administrator created.", 201, result)
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error("Account ID, email, or username already exists.", 409)
        return error("Account cannot be created.", 400)
    except Exception:
        return error("Account operation failed.", 500)


def get_admins_control():
    try:
        return success("Administrators retrieved.", 200, get_admins_service())
    except Exception:
        return error("Account operation failed.", 500)


def update_admin_control(id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    try:
        return success("Administrator updated.", 200, update_admin_service(id, body))
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error("Account ID, email, or username already exists.", 409)
        return error("Account cannot be updated.", 400)
    except Exception:
        return error("Account operation failed.", 500)


def set_account_status_control(id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    try:
        result = set_account_status_service(id, body.get("status"), g.user_id)
        return success("Account status updated.", 200, result)
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        return error("Account operation failed.", 500)
