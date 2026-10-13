from flask import Blueprint
from backend.utils.jwt import token_required, role_required
from backend.controllers.users_controller import (
    get_users_control,
    get_user_by_id_control,
    create_admin_control,
    get_admins_control,
    update_admin_control,
    set_account_status_control,
)


users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def get_users():
    return get_users_control()


@users_bp.route("/users/<int:id>", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def get_by_id(id):
    return get_user_by_id_control(id)


@users_bp.post("/admins")
@token_required
@role_required("Admin")
def create_admin():
    return create_admin_control()


@users_bp.get("/admins")
@token_required
@role_required("Admin")
def get_admins():
    return get_admins_control()


@users_bp.put("/admins/<int:id>")
@token_required
@role_required("Admin")
def update_admin(id):
    return update_admin_control(id)


@users_bp.patch("/users/<int:id>/status")
@token_required
@role_required("Admin")
def set_account_status(id):
    return set_account_status_control(id)

