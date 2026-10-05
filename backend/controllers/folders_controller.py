from flask import current_app, g, request

from backend.services import folders_service as service
from backend.utils.api_response import error, success
from backend.utils.folder_errors import FolderError


def initialize_roots_control():
    body = request.get_json(silent=True)

    if request.get_data() and body != {}:
        return error(
            "Send an empty body or an empty JSON object.",
            400,
        )

    return respond(
        service.initialize_roots_service,
        "Workspace roots are ready.",
    )


def list_roots_control():
    return respond(
        service.list_roots_service,
        "Root folders retrieved.",
    )


def open_folder_control(folder_id):
    if set(request.args) - {"limit", "offset"}:
        return error(
            "Only limit and offset query parameters are supported.",
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
        service.open_folder_service,
        "Folder opened.",
        200,
        folder_id,
        limit,
        offset,
    )
def create_folder_control():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return error(
            "Request body must be a valid JSON object.",
            400
        )

    if set(body) != {"parent_folder_id", "name"}:
        return error(
            "Send only parent_folder_id and name.",
            400
        )

    return respond(
        service.create_folder_service,
        "Folder created.",
        201,
        body["parent_folder_id"],
        body["name"]
    )


def respond(operation, message, status_code=200, *args):
    try:
        data = operation(g.user_id, *args)

        return success(
            message,
            status_code,
            data
        )

    except FolderError as exc:
        return error(
            str(exc),
            exc.status_code
        )

    except Exception:
        current_app.logger.exception(
            "Folder operation failed"
        )

        return error(
            "Folder operation failed. Please try again.",
            500
        )