from flask import request

from backend.controllers.folders_controller import respond
from backend.services.projectFiles_services import (
    list_project_files_service,
    upload_project_files_service,
)
from backend.utils.api_response import error


def list_project_files_control(folder_id, project_id):
    if set(request.args) - {"limit", "offset"}:
        return error(
            "Only limit and offset are supported.",
            400,
        )

    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return error(
            "limit and offset must be integers.",
            400,
        )

    if not 1 <= limit <= 200 or offset < 0:
        return error(
            "limit must be 1 to 200; offset must be nonnegative.",
            400,
        )

    return respond(
        list_project_files_service,
        "Project files retrieved.",
        200,
        folder_id,
        project_id,
        limit,
        offset,
    )

def upload_project_file_control(folder_id, project_id):
    if request.mimetype != "multipart/form-data":
        return error(
            "Use form-data with file fields named file.",
            400,
        )

    if request.form or set(request.files) != {"file"}:
        return error(
            "Send files using only the file field.",
            400,
        )

    uploads = request.files.getlist("file")

    return respond(
        upload_project_files_service,
        "Files uploaded.",
        201,
        folder_id,
        project_id,
        uploads,
    )