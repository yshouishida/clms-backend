from flask import request
from pymysql.err import IntegrityError

from backend.utils.api_response import success, error
from backend.services.instructors_service import (
    get_instructors_servie,
    get_by_id_service,
    add_instructor_service,
    update_instructor_service,
    delete_instructor_service,
)


#===============================================
# VALIDATE COMMON INSTRUCTOR FIELDS
#===============================================
def _validate_instructor_input(user_input):
    if not isinstance(user_input, dict):
        return error("Request body must be a valid JSON object.", 400)

    text_limits = {
        "account_id": 30,
        "first_name": 50,
        "last_name": 50,
        "email": 100,
        "username": 50,
        "employee_number": 30
    }

    for field, max_length in text_limits.items():
        value = user_input.get(field)

        if not isinstance(value, str) or not value.strip():
            return error(
                f"{field} is required and must be a string.",
                400
            )

        value = value.strip()

        if len(value) > max_length:
            return error(
                f"{field} must not exceed {max_length} characters.",
                400
            )

        user_input[field] = value

    return None


#===============================================
# GET INSTRUCTORS
#===============================================
def get_instructors_control():
    instructors = get_instructors_servie()

    if instructors is None:
        return error("Instructors are not found.", 404)

    return success(
        "Instructors retrieved successfully!",
        200,
        instructors
    )


#===============================================
# GET INSTRUCTOR BY ID
#===============================================
def get_by_id_control(id):
    instructor = get_by_id_service(id)

    if instructor is None:
        return error("Instructor is not found.", 404)

    return success(
        "Instructor retrieved successfully!",
        200,
        instructor
    )


#===============================================
# ADD INSTRUCTOR
#===============================================
def add_instructor_control():
    user_input = request.get_json(silent=True)

    validation_error = _validate_instructor_input(user_input)

    if validation_error is not None:
        return validation_error

    password = user_input.get("password")

    if not isinstance(password, str) or not password:
        return error("Password is required and must be a string.", 400)

    role_id = user_input.get("role_id")

    if type(role_id) is not int or role_id < 1:
        return error("role_id must be a positive integer.", 400)

    try:
        result = add_instructor_service(
            user_input["account_id"],
            user_input["first_name"],
            user_input["last_name"],
            user_input["email"],
            user_input["username"],
            password,
            role_id,
            user_input["employee_number"]
        )

    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error(
                "Account ID, email, username, or employee number already exists.",
                409
            )

        if exc.args[0] == 1452:
            return error("The selected role does not exist.", 400)

        raise

    return success("Instructor added successfully!", 201, result)


#===============================================
# UPDATE INSTRUCTOR
#===============================================
def update_instructor_control(id):
    user_input = request.get_json(silent=True)

    validation_error = _validate_instructor_input(user_input)

    if validation_error is not None:
        return validation_error

    try:
        result = update_instructor_service(
            id,
            user_input["account_id"],
            user_input["first_name"],
            user_input["last_name"],
            user_input["email"],
            user_input["username"],
            user_input["employee_number"]
        )

    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error(
                "Account ID, email, username, or employee number already exists.",
                409
            )

        raise

    if result is None:
        return error("Instructor is not found.", 404)

    return success("Instructor updated successfully!", 200, result)


#===============================================
# SOFT DELETE INSTRUCTOR
#===============================================
def delete_instructor_control(id):
    result = delete_instructor_service(id)

    if result is None:
        return error("Instructor is not found.", 404)

    return success("Instructor deleted successfully!", 200, result)