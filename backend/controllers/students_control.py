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

def add_student_control():
    user_input = request.get_json()
    
    result = add_student_service(
        user_input.get("account_id"),
        user_input.get("first_name"),
        user_input.get("last_name"),
        user_input.get("email"),
        user_input.get("username"),
        user_input.get("password_hash"),
        user_input.get("role_id"),
        user_input.get("student_number"),
        user_input.get("program"),
        user_input.get("year_level"),
        user_input.get("section")
    )

    if result is None:
        return error("Unable to add student.", 400)

    return success("Student added successfully!", 201)

