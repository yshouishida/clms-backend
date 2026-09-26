from backend.repositories.students_repository import (
    get_students_repo,
    get_by_id_repo
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

