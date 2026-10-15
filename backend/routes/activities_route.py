from flask import Blueprint

from backend.controllers.activities_controller import (
    archive_activity_control,
    create_activity_control,
    download_submission_file_control,
    get_activity_control,
    list_activity_submissions_control,
    list_submission_versions_control,
    list_activities_control,
    submit_activity_control,
    update_activity_control,
    update_activity_status_control,
)
from backend.utils.jwt import role_required, token_required


activities_bp = Blueprint("activities", __name__)


@activities_bp.route(
    "/classes/<int:class_id>/activities", methods=["GET"]
)
@token_required
@role_required("Admin", "Instructor", "Student")
def list_activities(class_id):
    return list_activities_control(class_id)


@activities_bp.route(
    "/classes/<int:class_id>/activities", methods=["POST"]
)
@token_required
@role_required("Instructor")
def create_activity(class_id):
    return create_activity_control(class_id)


@activities_bp.route("/activities/<int:activity_id>", methods=["GET"])
@token_required
@role_required("Admin", "Instructor", "Student")
def get_activity(activity_id):
    return get_activity_control(activity_id)


@activities_bp.route("/activities/<int:activity_id>", methods=["PUT"])
@token_required
@role_required("Admin", "Instructor")
def update_activity(activity_id):
    return update_activity_control(activity_id)


@activities_bp.route(
    "/activities/<int:activity_id>/status", methods=["PUT"]
)
@token_required
@role_required("Admin", "Instructor")
def update_activity_status(activity_id):
    return update_activity_status_control(activity_id)


@activities_bp.route("/activities/<int:activity_id>", methods=["DELETE"])
@token_required
@role_required("Admin", "Instructor")
def archive_activity(activity_id):
    return archive_activity_control(activity_id)


@activities_bp.route(
    "/activities/<int:activity_id>/submissions", methods=["GET"]
)
@token_required
@role_required("Admin", "Instructor", "Student")
def list_activity_submissions(activity_id):
    return list_activity_submissions_control(activity_id)


@activities_bp.post("/activities/<int:activity_id>/submissions")
@token_required
@role_required("Student")
def submit_activity(activity_id):
    return submit_activity_control(activity_id)


@activities_bp.get("/submissions/<int:submission_id>/versions")
@token_required
@role_required("Admin", "Instructor", "Student")
def list_submission_versions(submission_id):
    return list_submission_versions_control(submission_id)


@activities_bp.get(
    "/submissions/<int:submission_id>/versions/<int:version_number>"
    "/files/<int:project_version_id>"
)
@token_required
@role_required("Admin", "Instructor", "Student")
def download_submission_file(submission_id, version_number, project_version_id):
    return download_submission_file_control(
        submission_id, version_number, project_version_id
    )
