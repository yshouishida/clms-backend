from flask import Blueprint

from backend.controllers.instructors_control import (
    get_instructors_control,
    get_by_id_control
)

instructors_bp = Blueprint("instructors", __name__)


@instructors_bp.route("/instructors", methods=["GET"])
def get_instructors():
    return get_instructors_control()

@instructors_bp.route("/instructors/<int:id>", methods=["GET"])
def get_by_id(id):
    return get_by_id_control(id)
