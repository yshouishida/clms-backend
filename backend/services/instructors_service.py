from werkzeug.security import generate_password_hash

from backend.repositories.instructors_repository import (
    get_instructiors_repo,
    get_by_id_repo,
    add_instructor_repo,
    update_instructor_repo,
    delete_instructor_repo,
)


def get_instructors_servie():
    return get_instructiors_repo()


def get_by_id_service(id):
    return get_by_id_repo(id)


def add_instructor_service(
    account_id,
    first_name,
    last_name,
    email,
    username,
    password,
    role_id,
    employee_number
):
    password_hash = generate_password_hash(password)

    return add_instructor_repo(
        account_id,
        first_name,
        last_name,
        email,
        username,
        password_hash,
        role_id,
        employee_number
    )


def update_instructor_service(
    instructor_id,
    account_id,
    first_name,
    last_name,
    email,
    username,
    employee_number
):
    return update_instructor_repo(
        instructor_id,
        account_id,
        first_name,
        last_name,
        email,
        username,
        employee_number
    )


def delete_instructor_service(instructor_id):
    return delete_instructor_repo(instructor_id)