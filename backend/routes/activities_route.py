from flask import Blueprint

from backend.controllers.activities_controller import (
    create_activity_control,
    get_activity_control,
    list_activities_control,
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