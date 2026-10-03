from backend.utils.api_response import success, error
from pymysql.err import IntegrityError
from flask import request

from backend.services.students_service import (
    get_students_service,
    get_by_id_service,
    add_student_service,
    update_student_service,
    delete_student_service,
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
    user_input = request.get_json(silent=True)

    if not isinstance(user_input, dict):
        return error("Request body must be a valid JSON object.", 400)

    text_limits = {
        "account_id": 30,
        "first_name": 50,
        "last_name": 50,
        "email": 100,
        "username": 50,
        "student_number": 30,
        "program": 100
    }

    for field, max_length in text_limits.items():
        value = user_input.get(field)

        if not isinstance(value, str) or not value.strip():
            return error(f"{field} is required and must be a string.", 400)

        value = value.strip()

        if len(value) > max_length:
            return error(
                f"{field} must not exceed {max_length} characters.",
                400
            )

        user_input[field] = value

    password = user_input.get("password")

    if not isinstance(password, str) or not password:
        return error("Password is required and must be a string.", 400)

    role_id = user_input.get("role_id")
    year_level = user_input.get("year_level")

    if type(role_id) is not int or role_id < 1:
        return error("role_id must be a positive integer.", 400)

    if type(year_level) is not int or year_level < 1:
        return error("year_level must be a positive integer.", 400)

    section = user_input.get("section")

    if section is not None:
        if not isinstance(section, str):
            return error("section must be a string.", 400)

        section = section.strip()

        if len(section) > 30:
            return error("section must not exceed 30 characters.", 400)

        section = section or None

    try:
        result = add_student_service(
            user_input["account_id"],
            user_input["first_name"],
            user_input["last_name"],
            user_input["email"],
            user_input["username"],
            password,
            role_id,
            user_input["student_number"],
            user_input["program"],
            year_level,
            section
        )

    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error(
                "Account ID, email, username, or student number already exists.",
                409
            )

        if exc.args[0] == 1452:
            return error("The selected role does not exist.", 400)

        raise

    return success("Student added successfully!", 201, result)

#===============================================
# UPDATE STUDENT
#===============================================
def update_student_control(id):
    user_input = request.get_json(silent=True)

    if not isinstance(user_input, dict):
        return error("Request body must be a valid JSON object.", 400)

    text_limits = {
        "account_id": 30,
        "first_name": 50,
        "last_name": 50,
        "email": 100,
        "username": 50,
        "student_number": 30,
        "program": 100
    }

    for field, max_length in text_limits.items():
        value = user_input.get(field)

        if not isinstance(value, str) or not value.strip():
            return error(f"{field} is required and must be a string.", 400)

        value = value.strip()

        if len(value) > max_length:
            return error(
                f"{field} must not exceed {max_length} characters.",
                400
            )

        user_input[field] = value

    year_level = user_input.get("year_level")

    if type(year_level) is not int or year_level < 1:
        return error("year_level must be a positive integer.", 400)

    section = user_input.get("section")

    if section is not None:
        if not isinstance(section, str):
            return error("section must be a string.", 400)

        section = section.strip()

        if len(section) > 30:
            return error("section must not exceed 30 characters.", 400)

        section = section or None

    try:
        result = update_student_service(
            id,
            user_input["account_id"],
            user_input["first_name"],
            user_input["last_name"],
            user_input["email"],
            user_input["username"],
            user_input["student_number"],
            user_input["program"],
            year_level,
            section
        )

    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error(
                "Account ID, email, username, or student number already exists.",
                409
            )

        raise

    if result is None:
        return error("Student is not found.", 404)

    return success("Student updated successfully!", 200, result)


#===============================================
# SOFT DELETE STUDENT
#===============================================
def delete_student_control(id):
    result = delete_student_service(id)

    if result is None:
        return error("Student is not found.", 404)

    return success("Student deleted successfully!", 200, result)

