import json
from datetime import datetime
from decimal import Decimal

from flask import current_app, g, request, send_file
from pymysql.err import IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from backend.repositories import captures_repository, inventory_repository, monitoring_repository
from backend.services import captures_service, inventory_service, monitoring_service
from backend.utils.api_response import error, success
from backend.utils.domain_error import DomainError


def response_data(value):
    if isinstance(value, datetime):
        return value.isoformat() + "Z"
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: response_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [response_data(item) for item in value]
    return value


def respond(action, message, status=200, workstation_id=None):
    try:
        result = action()
        if isinstance(result, tuple):
            result, status = result
        return success(message, status, response_data(result))
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except IntegrityError:
        return error("A unique value or related record conflicts with this request.", 409)
    except OperationalError as exc:
        if exc.args and exc.args[0] in (1205, 1213):
            return error("Concurrent operation; retry the request.", 409)
        current_app.logger.error("Monitoring database operation failed")
        return error("Monitoring storage is temporarily unavailable.", 503)
    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception("Monitoring operation failed")
        try:
            with inventory_repository.inventory_transaction() as cursor:
                inventory_repository.system_log_repo(
                    cursor, workstation_id, "Error", "MonitoringBackend",
                    "Monitoring operation failed.",
                )
        except Exception:
            current_app.logger.error("Unable to record monitoring failure")
        return error("Unable to process monitoring request.", 500)


def json_body():
    if not request.is_json:
        raise DomainError("Content-Type must be application/json.", 415)
    raw = request.stream.read(65537)
    if len(raw) > 65536:
        raise DomainError("JSON request exceeds 64 KiB.", 413)
    try:
        body = json.loads(raw)
        json.dumps(body, ensure_ascii=False).encode("utf-8")
    except (ValueError, UnicodeError):
        raise DomainError("Request body must be valid JSON.")
    if not isinstance(body, dict):
        raise DomainError("Request body must be a JSON object.")
    return body


def query_options(parent_name=None):
    allowed = {"limit", "offset"} | ({parent_name} if parent_name else set())
    if set(request.args) - allowed or any(len(request.args.getlist(key)) != 1 for key in request.args):
        raise DomainError("Unsupported or repeated query parameter.")
    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
        parent = int(request.args[parent_name]) if parent_name and parent_name in request.args else None
    except ValueError:
        raise DomainError("Query identifiers and pagination must be integers.")
    if not 1 <= limit <= 1000 or offset < 0 or (parent is not None and parent < 1):
        raise DomainError("Invalid pagination or identifier.")
    return limit, offset, parent


def inventory_list_control(kind):
    def action():
        if request.method == "POST":
            if g.user_role != "Admin":
                raise DomainError("Administrator access is required.", 403)
            return inventory_service.save_inventory_service(kind, json_body(), g.user_id), 201
        parent_name = (
            "laboratory_id" if kind == "workstations"
            else "workstation_id" if kind in inventory_repository.DEVICE_KINDS
            else None
        )
        return inventory_service.list_inventory_service(kind, *query_options(parent_name))
    return respond(action, "Inventory request completed.")


def inventory_detail_control(kind, record_id):
    def action():
        if request.method == "PATCH":
            if g.user_role != "Admin":
                raise DomainError("Administrator access is required.", 403)
            return inventory_service.save_inventory_service(kind, json_body(), g.user_id, record_id)
        return inventory_service.get_inventory_service(kind, record_id)
    return respond(action, "Inventory request completed.")


def dashboard_control():
    def action():
        if set(request.args) - {"laboratory_id"}:
            raise DomainError("Only laboratory_id is supported.")
        _, _, laboratory_id = query_options("laboratory_id")
        return monitoring_service.dashboard_service(laboratory_id, g.user_role == "Admin")
    return respond(action, "Workstation dashboard retrieved.")


def history_control(workstation_id):
    def action():
        limit, offset, _ = query_options()
        with inventory_repository.inventory_transaction() as cursor:
            return monitoring_repository.monitoring_history_repo(cursor, workstation_id, limit, offset)
    return respond(action, "Monitoring history retrieved.")


def logs_control():
    def action():
        limit, offset, workstation_id = query_options("workstation_id")
        with inventory_repository.inventory_transaction() as cursor:
            return monitoring_repository.logs_repo(cursor, workstation_id, limit, offset)
    return respond(action, "System logs retrieved.")


def heartbeat_control(workstation_id):
    return respond(lambda: monitoring_service.heartbeat_service(workstation_id, json_body()),
                   "Heartbeat accepted.", workstation_id=workstation_id)


def agent_configuration_control(workstation_id):
    return respond(lambda: monitoring_service.agent_configuration_service(workstation_id),
                   "Agent configuration retrieved.", workstation_id=workstation_id)


def agent_error_control(workstation_id):
    return respond(lambda: monitoring_service.agent_error_service(workstation_id, json_body()),
                   "Agent error recorded.", 201, workstation_id)


def capture_upload_control(workstation_id):
    def action():
        if request.content_length is None:
            raise DomainError("Content-Length is required for snapshot uploads.", 411)
        if request.content_length > current_app.config["SNAPSHOT_MAX_BYTES"] + 65536:
            raise DomainError("Snapshot request is too large.", 413)
        if request.mimetype != "multipart/form-data":
            raise DomainError("Use multipart/form-data.", 415)
        if set(request.files) != {"image"} or len(request.files.getlist("image")) != 1:
            raise DomainError("Send exactly one image file.")
        if (
            set(request.form) != {"session_id", "camera_id", "captured_at"}
            or any(len(request.form.getlist(key)) != 1 for key in request.form)
        ):
            raise DomainError("Send session_id, camera_id, and captured_at once each.")
        fields = request.form.to_dict()
        try:
            fields["session_id"] = int(fields["session_id"])
            fields["camera_id"] = int(fields["camera_id"])
        except ValueError:
            raise DomainError("session_id and camera_id must be integers.")
        return captures_service.upload_capture_service(workstation_id, fields, request.files["image"])
    return respond(action, "Login snapshot stored.", workstation_id=workstation_id)


def capture_failure_control(workstation_id):
    return respond(lambda: captures_service.capture_failure_service(workstation_id, json_body()),
                   "Capture failure recorded.", workstation_id=workstation_id)


def capture_list_control():
    def action():
        limit, offset, session_id = query_options("session_id")
        with inventory_repository.inventory_transaction() as cursor:
            return captures_repository.list_captures_repo(cursor, g.user_id, g.user_role, limit, offset, session_id)
    return respond(action, "Camera capture metadata retrieved.")


def capture_detail_control(capture_id):
    return respond(lambda: captures_service.get_capture_service(capture_id, g.user_id, g.user_role),
                   "Camera capture metadata retrieved.")


def capture_download_control(capture_id):
    try:
        path = captures_service.get_capture_service(capture_id, g.user_id, g.user_role, True)
        response = send_file(
            path, mimetype="image/png", as_attachment=True,
            download_name=f"capture-{capture_id}.png", conditional=False,
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response
    except DomainError as exc:
        return error(str(exc), exc.status_code)
    except OSError:
        return error("Snapshot file is unavailable.", 404)


def capture_summary_control():
    def action():
        with inventory_repository.inventory_transaction() as cursor:
            return captures_repository.capture_summary_repo(cursor)
    return respond(action, "Capture summary retrieved.")
