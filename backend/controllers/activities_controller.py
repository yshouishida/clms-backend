from flask import g, request

from backend.services import activities_service
from backend.services.activities_service import ActivitiesError
from backend.utils.api_response import error, success


def _respond(operation, message, status_code, *args):
    try:
        result = operation(*args)
    except ActivitiesError as exc:
        return error(str(exc), exc.status_code)
    return success(message, status_code, result)


def list_activities_control(class_id):
    return _respond(
        activities_service.list_activities_service,
        "Activities retrieved.",
        200,
        g.user_id,
        g.user_role,
        class_id,
    )


def get_activity_control(activity_id):
    return _respond(
        activities_service.get_activity_service,
        "Activity retrieved.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
    )


def create_activity_control(class_id):
    body = request.get_json(silent=True)
    allowed = {"activity_name", "instructions", "due_date"}
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    if set(body) != allowed:
        return error(
            "Request must contain activity_name, instructions, and due_date only.",
            400,
        )
    return _respond(
        activities_service.create_activity_service,
        "Activity created.",
        201,
        g.user_id,
        g.user_role,
        class_id,
        body["activity_name"],
        body["instructions"],
        body["due_date"],
    )


def update_activity_control(activity_id):
    body = request.get_json(silent=True)
    allowed = {"activity_name", "instructions", "due_date"}
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    if set(body) != allowed:
        return error(
            "Request must contain activity_name, instructions, and due_date only.",
            400,
        )
    return _respond(
        activities_service.update_activity_service,
        "Activity updated.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
        body["activity_name"],
        body["instructions"],
        body["due_date"],
    )


def update_activity_status_control(activity_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"status"}:
        return error("Request body must contain only status.", 400)
    return _respond(
        activities_service.update_activity_status_service,
        "Activity status updated.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
        body["status"],
    )