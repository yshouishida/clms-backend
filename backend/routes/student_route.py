from flask import Blueprint

from backend.controllers.student_control import (
    get_students_control,
    get_by_id_control
)

students_bp = Blueprint("students", __name__)


@students_bp.route("/students", methods=["GET"])
def get_students():
    return get_students_control()


@students_bp.route("/students/<int:id>", methods=["GET"])
def get_by_id(id):
    return get_by_id_control(id)