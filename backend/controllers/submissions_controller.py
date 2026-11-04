"""HTTP validation and responses for the submission workflow."""
from io import BytesIO

from flask import current_app, g, request, send_file

from backend.services import submissions_service as service
from backend.utils.api_response import error, success
from backend.utils.folder_errors import FolderError


def _call(operation, message, *args):
    try:
        result = operation(g.user_id, *args)
        if isinstance(result, tuple) and operation is service.create_submission_service:
            data, status_code = result
            if status_code == 200:
                message = "Existing submission retrieved; no new attempt was created."
        else:
            data, status_code = result, 200
        return success(message, status_code, data)
    except (service.SubmissionError, FolderError) as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Submission operation failed")
        return error("Submission operation failed. Please try again.", 500)


def create_submission_control(activity_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"project_id", "version_ids"}:
        return error("Send only project_id and version_ids in a JSON object.", 400)
    return _call(
        service.create_submission_service, "Submission saved.",
        activity_id, body["project_id"], body["version_ids"],
    )


def list_submissions_control(activity_id):
    if request.args:
        return error("Query parameters are not supported.", 400)
    return _call(service.list_submissions_service, "Submissions retrieved.", activity_id)


def get_submission_control(submission_id):
    if request.args:
        return error("Query parameters are not supported.", 400)
    return _call(service.get_submission_service, "Submission retrieved.", submission_id)


def review_submission_control(submission_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not set(body) <= {"status", "remarks"} or "status" not in body:
        return error("Send status and optional remarks in a JSON object.", 400)
    return _call(
        service.review_submission_service, "Submission reviewed.",
        submission_id, body["status"], body.get("remarks"),
    )


def download_submission_file_control(submission_id, submission_file_id):
    if request.args:
        return error("Query parameters are not supported.", 400)
    try:
        version = service.download_submission_file_service(
            g.user_id, submission_id, submission_file_id
        )
        response = send_file(
            BytesIO(version["content"]),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=version["file_name"],
            max_age=0,
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    except (service.SubmissionError, FolderError) as exc:
        return error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Submitted file download failed")
        return error("Submitted file download failed. Please try again.", 500)
