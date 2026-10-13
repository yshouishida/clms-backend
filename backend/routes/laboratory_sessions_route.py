from flask import Blueprint

from backend.controllers.laboratory_sessions_controller import (
    manual_workstation_login_control, rfid_workstation_login_control,
    logout_session_control, terminate_session_control, session_history_control,
    heartbeat_session_control,
    recovery_candidates_control, usage_summary_control,
)
from backend.utils.jwt import token_required, role_required

laboratory_sessions_bp = Blueprint("laboratory_sessions", __name__)


@laboratory_sessions_bp.post("/workstation/login/manual")
def manual_workstation_login():
    return manual_workstation_login_control()


@laboratory_sessions_bp.post("/workstation/login/rfid")
def rfid_workstation_login():
    return rfid_workstation_login_control()


@laboratory_sessions_bp.get("/laboratory-sessions")
@token_required
@role_required("Admin", "Student")
def session_history():
    return session_history_control()


@laboratory_sessions_bp.get("/laboratory-sessions/active")
@token_required
@role_required("Admin")
def active_sessions():
    return session_history_control(True)


@laboratory_sessions_bp.get("/laboratory-sessions/recovery-candidates")
@token_required
@role_required("Admin")
def recovery_candidates():
    return recovery_candidates_control()


@laboratory_sessions_bp.get("/laboratory-sessions/summary")
@token_required
@role_required("Admin")
def usage_summary():
    return usage_summary_control()


@laboratory_sessions_bp.post("/laboratory-sessions/<int:session_id>/logout")
@token_required
@role_required("Admin", "Student")
def logout_session(session_id):
    return logout_session_control(session_id)


@laboratory_sessions_bp.post("/laboratory-sessions/<int:session_id>/heartbeat")
@token_required
@role_required("Student")
def heartbeat_session(session_id):
    return heartbeat_session_control(session_id)


@laboratory_sessions_bp.patch("/laboratory-sessions/<int:session_id>/terminate")
@token_required
@role_required("Admin")
def terminate_session(session_id):
    return terminate_session_control(session_id)
