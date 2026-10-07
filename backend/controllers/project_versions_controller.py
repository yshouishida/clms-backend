from flask import request

from backend.controllers.folders_controller import respond
from backend.services.project_versions_service import (
    list_file_versions_service,
    upload_file_version_service,
)
from backend.utils.api_response import error


def list_file_versions_control(folder_id, project_id, file_id):
    if set(request.args) - {"limit", "offset"}:
        return error("Only limit and offset are supported.", 400)
    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return error("limit and offset must be integers.", 400)
    if not 1 <= limit <= 200 or offset < 0:
        return error(
            "limit must be 1 to 200; offset must be nonnegative.", 400
        )
    return respond(
        list_file_versions_service, "File versions retrieved.", 200,
        folder_id, project_id, file_id, limit, offset,
    )


def upload_file_version_control(folder_id, project_id, file_id):
    if request.args:
        return error("Query parameters are not supported.", 400)
    if request.mimetype != "multipart/form-data":
        return error("Use form-data with one file field named file.", 400)
    if (
        request.form
        or set(request.files) != {"file"}
        or len(request.files.getlist("file")) != 1
    ):
        return error("Send exactly one updated file using the file field.", 400)
    return respond(
        upload_file_version_service, "File version created.", 201,
        folder_id, project_id, file_id, request.files["file"],
    )
