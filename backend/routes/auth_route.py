from flask import Blueprint

from backend.controllers.auth_controller import login_control, logout_control
from backend.utils.jwt import token_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    return login_control()


@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout():
    return logout_control()