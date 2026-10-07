from flask import Blueprint

from backend.controllers.projectFiles_controller import (
    list_project_files_control,
    upload_project_file_control,
)
from backend.utils.jwt import token_required, role_required


project_files_bp = Blueprint("project_files", __name__)


@project_files_bp.route(
    "/folders/<int:folder_id>/projects/<int:project_id>/files",
    methods=["GET"],
)
@token_required
@role_required("Student")
def list_project_files(folder_id, project_id):
    return list_project_files_control(folder_id, project_id)


@project_files_bp.route(
    "/folders/<int:folder_id>/projects/<int:project_id>/files",
    methods=["POST"],
)
@token_required
@role_required("Student")
def upload_project_file(folder_id, project_id):
    return upload_project_file_control(folder_id, project_id)


