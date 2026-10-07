from flask import Blueprint

from backend.controllers.project_versions_controller import (
    list_file_versions_control,
    upload_file_version_control,
)
from backend.utils.jwt import token_required, role_required

project_versions_bp = Blueprint("project_versions", __name__)

VERSION_URL = (
    "/folders/<int:folder_id>/projects/<int:project_id>"
    "/files/<int:file_id>/versions"
)


@project_versions_bp.route(VERSION_URL, methods=["GET"])
@token_required
@role_required("Student")
def list_file_versions(folder_id, project_id, file_id):
    return list_file_versions_control(folder_id, project_id, file_id)


@project_versions_bp.route(VERSION_URL, methods=["POST"])
@token_required
@role_required("Student")
def upload_file_version(folder_id, project_id, file_id):
    return upload_file_version_control(folder_id, project_id, file_id)
