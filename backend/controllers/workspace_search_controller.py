from flask import request

from backend.controllers.folders_controller import respond
from backend.services.workspace_search_service import search_workspace_service
from backend.utils.api_response import error


def search_workspace_control():
    allowed = {"q", "kind", "limit", "offset"}
    if set(request.args) - allowed:
        return error("Supported query parameters are q, kind, limit, and offset.", 400)

    query = request.args.get("q", "")
    kind = request.args.get("kind", "all")
    try:
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return error("limit and offset must be integers.", 400)
    if not 1 <= limit <= 100 or offset < 0:
        return error("limit must be 1 to 100; offset must be nonnegative.", 400)

    return respond(
        search_workspace_service,
        "Workspace search completed.",
        200,
        query,
        kind,
        limit,
        offset,
    )