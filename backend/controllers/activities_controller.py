from flask import current_app, g, request, send_file

from backend.services import activities_service
from backend.services.activities_service import ActivitiesError
from backend.services import submissions_service
from backend.services.submissions_service import SubmissionError
from backend.utils.api_response import error, success


def _respond(operation, message, status_code, *args):
    try:
        result = operation(*args)
    except ActivitiesError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Activities request failed")
        return error("Unable to process activities request.", 500)
    return success(message, status_code, result)


def list_activities_control(class_id):
    return _respond(
        activities_service.list_activities_service,
        "Activities retrieved.",
        200,
        g.user_id,
        g.user_role,
        class_id,
    )


def get_activity_control(activity_id):
    return _respond(
        activities_service.get_activity_service,
        "Activity retrieved.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
    )


def create_activity_control(class_id):
    body = request.get_json(silent=True)
    allowed = {"activity_name", "instructions", "due_date"}
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    if set(body) != allowed:
        return error(
            "Request must contain activity_name, instructions, and due_date only.",
            400,
        )
    return _respond(
        activities_service.create_activity_service,
        "Activity created.",
        201,
        g.user_id,
        g.user_role,
        class_id,
        body["activity_name"],
        body["instructions"],
        body["due_date"],
    )


def update_activity_control(activity_id):
    body = request.get_json(silent=True)
    allowed = {"activity_name", "instructions", "due_date"}
    if not isinstance(body, dict):
        return error("Request body must be a valid JSON object.", 400)
    if set(body) != allowed:
        return error(
            "Request must contain activity_name, instructions, and due_date only.",
            400,
        )
    return _respond(
        activities_service.update_activity_service,
        "Activity updated.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
        body["activity_name"],
        body["instructions"],
        body["due_date"],
    )


def update_activity_status_control(activity_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"status"}:
        return error("Request body must contain only status.", 400)
    return _respond(
        activities_service.update_activity_status_service,
        "Activity status updated.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
        body["status"],
    )


def archive_activity_control(activity_id):
    return _respond(
        activities_service.update_activity_status_service,
        "Activity archived.",
        200,
        g.user_id,
        g.user_role,
        activity_id,
        "Archived",
    )


def _submission_response(operation, message, *args):
    try:
        result = operation(*args)
        status = 200
        if isinstance(result, tuple):
            result, status = result
        return success(message, status, result)
    except SubmissionError as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Activity submission request failed")
        return error("Unable to process activity submission.", 500)


def submit_activity_control(activity_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"project_id", "file_ids"}:
        return error("Send only project_id and file_ids.", 400)
    return _submission_response(
        submissions_service.submit_activity_service,
        "Submission saved.",
        g.user_id,
        g.user_role,
        activity_id,
        body["project_id"],
        body["file_ids"],
    )


def list_activity_submissions_control(activity_id):
    return _submission_response(
        submissions_service.list_activity_submissions_service,
        "Activity submissions retrieved.",
        g.user_id,
        g.user_role,
        activity_id,
    )


def list_submission_versions_control(submission_id):
    return _submission_response(
        submissions_service.list_submission_versions_service,
        "Submission versions retrieved.",
        g.user_id,
        g.user_role,
        submission_id,
    )


def download_submission_file_control(
    submission_id, version_number, project_version_id
):
    try:
        path, file_name = submissions_service.get_submission_file_service(
            g.user_id, g.user_role, submission_id, version_number,
            project_version_id,
        )
        response = send_file(
            path,
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=file_name,
            conditional=False,
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response
    except SubmissionError as exc:
        return error(str(exc), exc.status_code)
    except OSError:
        return error("Submitted file is unavailable.", 404)
    except Exception:
        current_app.logger.exception("Submission file download failed")
        return error("Unable to download submitted file.", 500)
