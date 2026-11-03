from flask import current_app, g, request

from backend.services import announcements_service
from backend.services.classes_service import ClassesError
from backend.utils.api_response import error, success


def _respond(operation, message, status=200):
    try:
        return success(message, status, operation())
    except ClassesError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Announcement request failed")
        return error("Unable to process announcement request.", 500)


def list_announcements_control(class_id):
    return _respond(
        lambda: announcements_service.list_announcements_service(
            g.user_id, g.user_role, class_id
        ),
        "Announcements retrieved.",
    )


def create_announcement_control(class_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"title", "content"}:
        return error("Send title and content only.", 400)
    return _respond(
        lambda: announcements_service.create_announcement_service(
            g.user_id, g.user_role, class_id, body["title"], body["content"]
        ),
        "Announcement created.",
        201,
    )


def update_announcement_control(announcement_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {
        "title", "content", "status"
    }:
        return error("Send title, content, and status only.", 400)
    return _respond(
        lambda: announcements_service.update_announcement_service(
            g.user_id, g.user_role, announcement_id,
            body["title"], body["content"], body["status"],
        ),
        "Announcement updated.",
    )
