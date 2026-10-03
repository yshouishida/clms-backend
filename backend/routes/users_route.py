from flask import Blueprint
from backend.utils.jwt import token_required, role_required
from backend.controllers.users_controller import (
    get_users_control,
    get_user_by_id_control
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

