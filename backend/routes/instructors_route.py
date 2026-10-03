from flask import Blueprint

from backend.utils.jwt import token_required, role_required
from backend.controllers.instructors_controller import (
    get_instructors_control,
    get_by_id_control,
    add_instructor_control,
    update_instructor_control,
    delete_instructor_control,
)

instructors_bp = Blueprint("instructors", __name__)


@instructors_bp.route("/instructors", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def get_instructors():
    return get_instructors_control()


@instructors_bp.route("/instructors/<int:id>", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def get_by_id(id):
    return get_by_id_control(id)


@instructors_bp.route("/instructors", methods=["POST"])
@token_required
@role_required("Admin")
def add_instructor():
    return add_instructor_control()


@instructors_bp.route("/instructors/<int:id>", methods=["PUT"])
@token_required
@role_required("Admin")
def update_instructor(id):
    return update_instructor_control(id)


@instructors_bp.route("/instructors/<int:id>", methods=["DELETE"])
@token_required
@role_required("Admin")
def delete_instructor(id):
    return delete_instructor_control(id)