from flask import request

from backend.controllers.folders_controller import respond
from backend.services.project_snapshots_service import (
    create_project_snapshot_service,
    list_project_snapshots_service,
    restore_project_snapshot_service,
)
from backend.utils.api_response import error


def create_project_snapshot_control(folder_id, project_id):
    body = request.get_json(silent=True)
    if not request.get_data():
        body = {}
    if not isinstance(body, dict) or set(body) - {"snapshot_name"}:
        return error("Send an optional snapshot_name in a JSON object.", 400)
    return respond(
        create_project_snapshot_service,
        "Project snapshot created.",
        201,
        folder_id,
        project_id,
        body.get("snapshot_name"),
    )


def list_project_snapshots_control(folder_id, project_id):
    if set(request.args) - {"limit", "offset"}:
        return error("Only limit and offset are supported.", 400)
    try:
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return error("limit and offset must be integers.", 400)
    if not 1 <= limit <= 200 or offset < 0:
        return error("limit must be 1 to 200; offset must be nonnegative.", 400)
    return respond(
        list_project_snapshots_service,
        "Project snapshots retrieved.",
        200,
        folder_id,
        project_id,
        limit,
        offset,
    )


def restore_project_snapshot_control(folder_id, project_id, snapshot_id):
    if request.get_data() or request.args:
        return error("Snapshot restoration does not accept a body or query parameters.", 400)
    return respond(
        restore_project_snapshot_service,
        "Project snapshot restored.",
        200,
        folder_id,
        project_id,
        snapshot_id,
    )
