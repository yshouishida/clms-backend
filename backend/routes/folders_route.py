from flask import Blueprint

from backend.controllers.folders_controller import (
    create_folder_control,
    initialize_roots_control,
    list_roots_control,
    open_folder_control,
    rename_folder_control,
    delete_folder_control,
    restore_folder_control,
)

from backend.controllers.workspace_search_controller import search_workspace_control

from backend.utils.jwt import token_required, role_required


folders_bp = Blueprint("folders", __name__)


@folders_bp.route("/folders/initialize", methods=["POST"])
@token_required
@role_required("Student")
def initialize_roots():
    return initialize_roots_control()


@folders_bp.route("/folders/roots", methods=["GET"])
@token_required
@role_required("Student")
def list_roots():
    return list_roots_control()


@folders_bp.route("/folders/<int:folder_id>", methods=["GET"])
@token_required
@role_required("Student")
def open_folder(folder_id):
    return open_folder_control(folder_id)


@folders_bp.route("/folders", methods=["POST"])
@token_required
@role_required("Student")
def create_folder():
    return create_folder_control()

@folders_bp.route("/folders/<int:folder_id>", methods=["PATCH"])
@token_required
@role_required("Student")
def rename_folder(folder_id):
    return rename_folder_control(folder_id)


@folders_bp.route("/folders/<int:folder_id>", methods=["DELETE"])
@token_required
@role_required("Student")
def delete_folder(folder_id):
    return delete_folder_control(folder_id)


@folders_bp.route("/folders/<int:folder_id>/restore", methods=["POST"])
@token_required
@role_required("Student")
def restore_folder(folder_id):
    return restore_folder_control(folder_id)


@folders_bp.route("/workspace/search", methods=["GET"])
@token_required
@role_required("Student")
def search_workspace():
    return search_workspace_control()
