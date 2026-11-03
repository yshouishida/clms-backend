from flask import Blueprint

from backend.controllers import announcements_controller
from backend.utils.jwt import role_required, token_required


announcements_bp = Blueprint("announcements", __name__)


@announcements_bp.get("/classes/<int:class_id>/announcements")
@token_required
@role_required("Admin", "Instructor", "Student")
def list_announcements(class_id):
    return announcements_controller.list_announcements_control(class_id)


@announcements_bp.post("/classes/<int:class_id>/announcements")
@token_required
@role_required("Admin", "Instructor")
def create_announcement(class_id):
    return announcements_controller.create_announcement_control(class_id)


@announcements_bp.put("/announcements/<int:announcement_id>")
@token_required
@role_required("Admin", "Instructor")
def update_announcement(announcement_id):
    return announcements_controller.update_announcement_control(
        announcement_id
    )
