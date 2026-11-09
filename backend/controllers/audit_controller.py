from flask import current_app, g, request
from decimal import Decimal

from backend.services import audit_service
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


def list_audit_events_control():
    allowed = {"limit", "offset", "user_id", "entity_name", "action"}
    if set(request.args) - allowed or any(
        len(request.args.getlist(key)) != 1 for key in request.args
    ):
        return error("Unsupported or repeated query parameter.", 400)
    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
        user_id = int(request.args["user_id"]) if "user_id" in request.args else None
    except ValueError:
        return error("limit, offset, and user_id must be integers.", 400)
    entity_name = request.args.get("entity_name")
    action = request.args.get("action")
    if not 1 <= limit <= 1000 or offset < 0 or (
        user_id is not None and user_id < 1
    ):
        return error("Invalid pagination or user_id.", 400)
    if entity_name is not None and (not entity_name.strip() or len(entity_name) > 100):
        return error("entity_name is invalid.", 400)
    if action is not None and (not action.strip() or len(action) > 100):
        return error("action is invalid.", 400)
    try:
        result = audit_service.list_audit_events_service(
            g.user_id, g.user_role, limit, offset, user_id, entity_name, action
        )
        return success("Audit history retrieved.", 200, _json_data(result))
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Audit history request failed")
        return error("Unable to retrieve audit history.", 500)
