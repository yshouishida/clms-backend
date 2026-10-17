from flask import Blueprint

from backend.controllers.projects_controller import (
    list_folder_projects_control,
    create_folder_project_control,
    update_folder_project_control,
    delete_folder_project_control,
    restore_folder_project_control,
)
from backend.controllers.project_snapshots_controller import (
    create_project_snapshot_control,
    list_project_snapshots_control,
    restore_project_snapshot_control,
)
from backend.utils.jwt import token_required, role_required


projects_bp = Blueprint("projects", __name__)
PROJECT_DETAIL_URL = "/folders/<int:folder_id>/projects/<int:project_id>"

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

@projects_bp.route(PROJECT_DETAIL_URL, methods=["PATCH"])
@token_required
@role_required("Student")
def update_folder_project(folder_id, project_id):
    return update_folder_project_control(folder_id, project_id)

@projects_bp.route(PROJECT_DETAIL_URL, methods=["DELETE"])
@token_required
@role_required("Student")
def delete_folder_project(folder_id, project_id):
    return delete_folder_project_control(folder_id, project_id)

@projects_bp.route(PROJECT_DETAIL_URL + "/restore", methods=["POST"])
@token_required
@role_required("Student")
def restore_folder_project(folder_id, project_id):
    return restore_folder_project_control(folder_id, project_id)

@projects_bp.route(
    "/folders/<int:folder_id>/projects/<int:project_id>/snapshots",
    methods=["POST"],
)
@token_required
@role_required("Student")
def create_project_snapshot(folder_id, project_id):
    return create_project_snapshot_control(folder_id, project_id)

@projects_bp.route(
    "/folders/<int:folder_id>/projects/<int:project_id>/snapshots",
    methods=["GET"],
)
@token_required
@role_required("Student")
def list_project_snapshots(folder_id, project_id):
    return list_project_snapshots_control(folder_id, project_id)

# snapshot_id is a UUID hex string stored in a JSON manifest, not a DB row ID.
@projects_bp.route(
    "/folders/<int:folder_id>/projects/<int:project_id>/snapshots/<snapshot_id>/restore",
    methods=["POST"],
)
@token_required
@role_required("Student")
def restore_project_snapshot(folder_id, project_id, snapshot_id):
    return restore_project_snapshot_control(folder_id, project_id, snapshot_id)