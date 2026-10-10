from flask import g, request

from backend.services.classes_service import ClassesError
from backend.services import classes_service
from backend.utils.api_response import error, success


def _respond(operation, message, status_code, *args):
    try:
        result = operation(*args)
    except ClassesError as exc:
        return error(str(exc), exc.status_code)
    return success(message, status_code, result)


def list_classes_control():
    return _respond(
        classes_service.list_classes_service,
        "Classes retrieved.",
        200,
        g.user_id,
        g.user_role,
    )


def get_class_control(class_id):
    return _respond(
        classes_service.get_class_service,
        "Class retrieved.",
        200,
        g.user_id,
        g.user_role,
        class_id,
    )


def create_class_control():
    body = request.get_json(silent=True)
    allowed = {"class_code", "class_name", "school_year", "semester", "description"}
    required = allowed - {"description"}
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    if set(body) - allowed:
        return error("Request contains unsupported fields.", 400)
    if required - set(body):
        return error("class_code, class_name, school_year, and semester are required.", 400)

    return _respond(
        classes_service.create_class_service,
        "Class created.",
        201,
        g.user_id,
        g.user_role,
        body["class_code"],
        body["class_name"],
        body["school_year"],
        body["semester"],
        body.get("description"),
    )


def update_class_control(class_id):
    body = request.get_json(silent=True)
    allowed = {"class_code", "class_name", "school_year", "semester", "description"}
    required = allowed - {"description"}
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    if set(body) - allowed:
        return error("Request contains unsupported fields.", 400)
    if required - set(body):
        return error("class_code, class_name, school_year, and semester are required.", 400)

    return _respond(
        classes_service.update_class_service,
        "Class updated.",
        200,
        g.user_id,
        g.user_role,
        class_id,
        body["class_code"],
        body["class_name"],
        body["school_year"],
        body["semester"],
        body.get("description"),
    )


def archive_class_control(class_id):
    return _respond(
        classes_service.archive_class_service,
        "Class archived.",
        200,
        g.user_id,
        g.user_role,
        class_id,
    )


def list_class_members_control(class_id):
    return _respond(
        classes_service.list_class_members_service,
        "Class members retrieved.",
        200,
        g.user_id,
        g.user_role,
        class_id,
    )


def enroll_student_control(class_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"student_id"}:
        return error("Request body must contain only student_id.", 400)
    return _respond(
        classes_service.enroll_student_service,
        "Student enrolled.",
        201,
        g.user_id,
        g.user_role,
        class_id,
        body["student_id"],
    )


def update_class_member_control(class_id, student_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"status"}:
        return error("Request body must contain only status.", 400)
    return _respond(
        classes_service.update_class_member_service,
        "Class membership updated.",
        200,
        g.user_id,
        g.user_role,
        class_id,
        student_id,
        body["status"],
    )