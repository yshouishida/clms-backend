from backend.utils.api_response import success, error
from flask import request

from backend.services.students_service import (
    get_students_service,
    get_by_id_service,
    add_student_service
)

def get_students_control():
    students = get_students_service()

    if students is None:
        return error("Students are not found.", 404)

    return success("Get successfully.", 200, students)


def get_by_id_control(id):
    student = get_by_id_service(id)

    if student is None:
        return error("Student is not found.", 404)

    return success("Get successfully.", 200, student)

