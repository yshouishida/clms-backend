from backend.repositories.students_repository import (
    get_students_repo,
    get_by_id_repo,
    add_student_repo
)


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
    password_hash, 
    role_id, 
    student_number, 
    program, 
    year_level, 
    section
):
    result = add_student_repo(
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

    if result is None:
        return None

    return result

