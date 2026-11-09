from flask import request, current_app, g, send_file

from backend.controllers.folders_controller import respond
from backend.services.projectFiles_services import (
    list_project_files_service,
    upload_project_files_service,
    download_project_file_service,
    rename_project_file_service,
    delete_project_file_service,
)
from backend.utils.folder_errors import FolderError
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

def download_project_file_control(folder_id, project_id, file_id):
    if request.args:
        return error("File download does not accept query parameters.", 400)
    try:
        item = download_project_file_service(
            g.user_id, folder_id, project_id, file_id
        )
        return send_file(
            item["path"],
            as_attachment=True,
            download_name=item["file_name"],
            mimetype=item["file_type"],
            conditional=True,
        )
    except FolderError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Project-file download failed")
        return error("File could not be downloaded.", 500)

def rename_project_file_control(folder_id, project_id, file_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"file_name"}:
        return error("Send a JSON object containing only file_name.", 400)
    return respond(
        rename_project_file_service,
        "File renamed.",
        200,
        folder_id,
        project_id,
        file_id,
        body["file_name"],
    )

def delete_project_file_control(folder_id, project_id, file_id):
    if request.get_data() or request.args:
        return error("DELETE file does not accept a body or query parameters.", 400)
    return respond(
        delete_project_file_service,
        "File deleted. Its stored contents and versions were retained for recovery.",
        200,
        folder_id,
        project_id,
        file_id,
    )