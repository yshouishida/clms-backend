from flask import Blueprint

from backend.utils.jwt import token_required, role_required
from backend.controllers.students_control import (
    get_students_control,
    get_by_id_control,
    add_student_control,
    update_student_control,
    delete_student_control,
)

students_bp = Blueprint("students", __name__)


@students_bp.route("/students", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def get_students():
    return get_students_control()


@students_bp.route("/students/<int:id>", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def get_by_id(id):
    return get_by_id_control(id)


@students_bp.route("/students", methods=["POST"])
@token_required
@role_required("Admin")
def add_student():
    return add_student_control()


@students_bp.route("/students/<int:id>", methods=["PUT"])
@token_required
@role_required("Admin")
def update_student(id):
    return update_student_control(id)


@students_bp.route("/students/<int:id>", methods=["DELETE"])
@token_required
@role_required("Admin")
def delete_student(id):
    return delete_student_control(id)