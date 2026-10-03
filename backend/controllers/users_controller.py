from backend.utils.api_response import success, error
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
    user = get_user_by_id_service(id)

    if user is None:
        return error("User is not found.", 404)

    return success("Get successfully.", 200, user)
