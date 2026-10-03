from backend.repositories.students_repository import (
    get_students_repo,
    get_by_id_repo,
    add_student_repo,
    update_student_repo,
    delete_student_repo,
)

from werkzeug.security import generate_password_hash


def get_students_service():
    students = get_students_repo()

    if students is None:
        return None

    return students

def get_by_id_service(id):
    student = get_by_id_repo(id)

    if student is None:
        return None

    return student


def add_student_service(
    account_id,
    first_name,
    last_name,
    email,
    username,
    password,
    role_id,
    student_number,
    program,
    year_level,
    section
):
    password_hash = generate_password_hash(password)

    return add_student_repo(
        account_id,
        first_name,
        last_name,
        email,
        username,
        password_hash,
        role_id,
        student_number,
        program,
        year_level,
        section
    )

#===============================================
# UPDATE STUDENT
#===============================================
def update_student_service(
    student_id,
    account_id,
    first_name,
    last_name,
    email,
    username,
    student_number,
    program,
    year_level,
    section
):
    return update_student_repo(
        student_id,
        account_id,
        first_name,
        last_name,
        email,
        username,
        student_number,
        program,
        year_level,
        section
    )


#===============================================
# SOFT DELETE STUDENT
#===============================================
def delete_student_service(student_id):
    return delete_student_repo(student_id)
