
from flask import current_app, g, request


from backend.utils.api_response import error, success
from backend.utils.folder_errors import FolderError
from backend.controllers.folders_controller import respond

from backend.services.projects_services import (
    list_folder_projects_service,
    create_folder_project_service,
)


def list_folder_projects_control(folder_id):
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
    list_folder_projects_service,
    "Projects retrieved.",
    200,
    folder_id,
    limit,
    offset,
   )

def create_folder_project_control(folder_id):
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return error(
            "Request body must be a valid JSON object.",
            400,
        )

    if set(body) - {"project_name", "description"}:
        return error(
            "Send only project_name and description.",
            400,
        )

    if "project_name" not in body:
        return error("project_name is required.", 400)

    return respond(
        create_folder_project_service,
        "Project created.",
        201,
        folder_id,
        body["project_name"],
        body.get("description"),
    )