from flask import Blueprint

from backend.controllers.projects_controller import (
    list_folder_projects_control,
    create_folder_project_control,
)
from backend.utils.jwt import token_required, role_required


projects_bp = Blueprint("projects", __name__)


@projects_bp.route(
    "/folders/<int:folder_id>/projects",
    methods=["GET"],
)
@token_required
@role_required("Student")
def list_folder_projects(folder_id):
    return list_folder_projects_control(folder_id)


@projects_bp.route(
    "/folders/<int:folder_id>/projects",
    methods=["POST"],
)
@token_required
@role_required("Student")
def create_folder_project(folder_id):
    return create_folder_project_control(folder_id)