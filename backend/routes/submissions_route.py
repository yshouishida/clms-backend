"""Student submission and owning-instructor review routes."""
from flask import Blueprint

from backend.controllers.submissions_controller import (
    create_submission_control,
    download_submission_file_control,
    get_submission_control,
    list_submissions_control,
    review_submission_control,
)
from backend.utils.jwt import role_required, token_required


submissions_bp = Blueprint("submissions", __name__)


@submissions_bp.route("/activities/<int:activity_id>/submissions", methods=["POST"])
@token_required
@role_required("Student")
def create_submission(activity_id):
    return create_submission_control(activity_id)


@submissions_bp.route("/activities/<int:activity_id>/submissions", methods=["GET"])
@token_required
@role_required("Instructor")
def list_submissions(activity_id):
    return list_submissions_control(activity_id)


@submissions_bp.route("/submissions/<int:submission_id>", methods=["GET"])
@token_required
@role_required("Instructor")
def get_submission(submission_id):
    return get_submission_control(submission_id)


@submissions_bp.route("/submissions/<int:submission_id>/review", methods=["PATCH"])
@token_required
@role_required("Instructor")
def review_submission(submission_id):
    return review_submission_control(submission_id)


@submissions_bp.route(
    "/submissions/<int:submission_id>/files/<int:submission_file_id>/content",
    methods=["GET"],
)
@token_required
@role_required("Instructor")
def download_submission_file(submission_id, submission_file_id):
    return download_submission_file_control(submission_id, submission_file_id)
