from flask import Blueprint

from backend.controllers.classes_controller import (
    archive_class_control,
    create_class_control,
    enroll_student_control,
    get_class_control,
    list_class_members_control,
    list_classes_control,
    update_class_control,
    update_class_member_control,
)
from backend.utils.jwt import role_required, token_required


classes_bp = Blueprint("classes", __name__)


@classes_bp.route("/classes", methods=["GET"])
@token_required
@role_required("Admin", "Instructor", "Student")
def list_classes():
    return list_classes_control()


@classes_bp.route("/classes", methods=["POST"])
@token_required
@role_required("Instructor")
def create_class():
    return create_class_control()


@classes_bp.route("/classes/<int:class_id>", methods=["GET"])
@token_required
@role_required("Admin", "Instructor", "Student")
def get_class(class_id):
    return get_class_control(class_id)


@classes_bp.route("/classes/<int:class_id>", methods=["PUT"])
@token_required
@role_required("Admin", "Instructor")
def update_class(class_id):
    return update_class_control(class_id)


@classes_bp.route("/classes/<int:class_id>", methods=["DELETE"])
@token_required
@role_required("Admin", "Instructor")
def archive_class(class_id):
    return archive_class_control(class_id)


@classes_bp.route("/classes/<int:class_id>/members", methods=["GET"])
@token_required
@role_required("Admin", "Instructor")
def list_class_members(class_id):
    return list_class_members_control(class_id)


@classes_bp.route("/classes/<int:class_id>/members", methods=["POST"])
@token_required
@role_required("Admin", "Instructor")
def enroll_student(class_id):
    return enroll_student_control(class_id)


@classes_bp.route(
    "/classes/<int:class_id>/members/<int:student_id>", methods=["PUT"]
)
@token_required
@role_required("Admin", "Instructor")
def update_class_member(class_id, student_id):
    return update_class_member_control(class_id, student_id)