from backend.repositories.users_repository import (
    get_users_repo,
    get_user_by_id_repo
)

def get_users_service():
    users = get_users_repo()

    if users is None:
        return None

    return users

def get_user_by_id_service(id):
    user = get_user_by_id_repo(id)

    if user is None:
        return None

    return user