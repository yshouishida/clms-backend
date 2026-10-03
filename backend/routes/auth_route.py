from flask import Blueprint
from backend.controllers.auth_controller import login_control

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    return login_control()