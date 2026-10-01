from flask import Blueprint

from backend.controllers.students_control import (
    get_students_control,
    get_by_id_control,
    add_student_control
)

students_bp = Blueprint("students", __name__)


@students_bp.route("/students", methods=["GET"])
def get_students():
    return get_students_control()


@students_bp.route("/students/<int:id>", methods=["GET"])
def get_by_id(id):
    return get_by_id_control(id)

@students_bp.route("/students", methods=["POST"])
def add_student():
    return add_student_control()