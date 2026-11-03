from flask import current_app, g, request
from decimal import Decimal

from backend.services import issues_service
from backend.utils.api_response import error, success
from backend.utils.domain_error import DomainError


def _json_data(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat() + ("Z" if value.tzinfo is None else "")
    if isinstance(value, dict):
        return {key: _json_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_data(item) for item in value]
    return value


def _respond(operation, message, status_code=200):
    try:
        result = operation()
        if isinstance(result, tuple):
            result, status_code = result
        return success(message, status_code, _json_data(result))
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("PC issue request failed")
        return error("Unable to process PC issue request.", 500)


def report_issue_control(workstation_id):
    body = request.get_json(silent=True)
    return _respond(
        lambda: issues_service.report_issue_service(
            g.user_id, g.user_role, workstation_id, body
        ),
        "PC issue reported.",
        201,
    )


def list_issues_control():
    allowed = {"limit", "offset", "workstation_id", "status"}
    if set(request.args) - allowed or any(
        len(request.args.getlist(key)) != 1 for key in request.args
    ):
        return error("Unsupported or repeated query parameter.", 400)
    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
        workstation_id = (
            int(request.args["workstation_id"])
            if "workstation_id" in request.args else None
        )
    except ValueError:
        return error("Pagination and workstation_id must be integers.", 400)
    if not 1 <= limit <= 1000 or offset < 0 or (
        workstation_id is not None and workstation_id < 1
    ):
        return error("Invalid pagination or workstation_id.", 400)
    return _respond(
        lambda: issues_service.list_issues_service(
            g.user_role, g.user_id, limit, offset, workstation_id,
            request.args.get("status"),
        ),
        "PC issues retrieved.",
    )


def update_issue_control(issue_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) - {"status", "resolution_details"}:
        return error("Send status and optional resolution_details only.", 400)
    if "status" not in body:
        return error("status is required.", 400)
    return _respond(
        lambda: issues_service.update_issue_service(
            g.user_id, g.user_role, issue_id, body["status"],
            body.get("resolution_details")
        ),
        "PC issue updated.",
    )
