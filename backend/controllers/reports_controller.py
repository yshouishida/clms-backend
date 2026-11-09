from flask import current_app, g, request
from decimal import Decimal

from backend.services import reports_service
from backend.utils.api_response import error, success
from backend.utils.domain_error import DomainError


def _json_data(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat() + ("Z" if getattr(value, "tzinfo", None) is None else "")
    if isinstance(value, dict):
        return {key: _json_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_data(item) for item in value]
    return value


def _respond(operation, message):
    try:
        return success(message, 200, _json_data(operation()))
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Report request failed")
        return error("Unable to process report request.", 500)


def _query_ids(allowed):
    if set(request.args) - allowed or any(
        len(request.args.getlist(key)) != 1 for key in request.args
    ):
        return None, error("Unsupported or repeated query parameter.", 400)
    try:
        values = {
            key: int(request.args[key])
            for key in allowed & set(request.args)
        }
    except ValueError:
        return None, error("Report identifiers must be integers.", 400)
    if any(value < 1 for value in values.values()):
        return None, error("Report identifiers must be positive integers.", 400)
    return values, None


def activities_report_control():
    values, response = _query_ids({"class_id"})
    if response:
        return response
    if "class_id" not in values:
        return error("class_id is required.", 400)
    return _respond(
        lambda: reports_service.activities_report_service(
            g.user_id, g.user_role, values["class_id"]
        ),
        "Activity report retrieved.",
    )


def submissions_report_control():
    values, response = _query_ids({"class_id", "activity_id"})
    if response:
        return response
    if "class_id" not in values:
        return error("class_id is required.", 400)
    return _respond(
        lambda: reports_service.submissions_report_service(
            g.user_id, g.user_role, values["class_id"],
            values.get("activity_id"),
        ),
        "Submission report retrieved.",
    )


def student_progress_report_control():
    values, response = _query_ids({"class_id", "student_id"})
    if response:
        return response
    if "class_id" not in values:
        return error("class_id is required.", 400)
    return _respond(
        lambda: reports_service.student_progress_report_service(
            g.user_id, g.user_role, values["class_id"],
            values.get("student_id"),
        ),
        "Student progress report retrieved.",
    )
