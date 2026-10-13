import hmac
import os

from backend.repositories.laboratory_sessions_repository import (
    rfid_identity_repo,
    create_session_repo,
    finish_session_repo,
    heartbeat_session_repo,
    session_history_repo,
    recovery_candidates_repo,
    usage_summary_repo,
)
from backend.repositories.auth_repository import record_auth_event_repo
from backend.services.auth_service import verify_credentials_service
from backend.utils.domain_error import DomainError
from backend.utils.jwt import create_access_token, validate_jwt_configuration
from backend.services.rfid_service import positive_id


def verify_workstation_key_service(provided_key):
    configured_key = os.getenv("WORKSTATION_API_KEY")

    if not configured_key or len(configured_key) < 32:
        raise DomainError("Workstation authentication is not configured.", 503)

    if not isinstance(provided_key, str) or not hmac.compare_digest(provided_key, configured_key):
        raise DomainError("Invalid workstation credentials.", 401)


def manual_workstation_login_service(username, password, workstation_id, ip_address=None):
    positive_id(workstation_id, "workstation_id")
    user = verify_credentials_service(username, password)

    if not user or user["role_name"] != "Student" or not user.get("student_id"):
        raise DomainError("Invalid student credentials.", 401)

    validate_jwt_configuration()
    session = create_session_repo(user["student_id"], workstation_id, "Manual")
    token = create_access_token(user["id"], user["role_name"], session["session_id"])

    record_auth_event_repo(
        user["id"],
        "WORKSTATION_LOGIN",
        "tblLaboratorySessions",
        session["session_id"],
        "Manual student workstation login.",
        ip_address
    )

    return {"access_token": token, "user": user, "session": session}


def rfid_workstation_login_service(card_uid, workstation_id, reader_id, ip_address=None):
    if not isinstance(card_uid, str) or not card_uid.strip() or len(card_uid.strip()) > 100:
        raise DomainError("card_uid is required and must be at most 100 characters.")

    positive_id(workstation_id, "workstation_id")
    positive_id(reader_id, "reader_id")

    identity = rfid_identity_repo(card_uid.strip())
    validate_jwt_configuration()
    session = create_session_repo(
        identity["student_id"],
        workstation_id,
        "RFID",
        identity["card_id"],
        reader_id
    )
    token = create_access_token(identity["user_id"], identity["role_name"], session["session_id"])

    record_auth_event_repo(
        identity["user_id"],
        "WORKSTATION_LOGIN",
        "tblLaboratorySessions",
        session["session_id"],
        "RFID student workstation login.",
        ip_address
    )

    user = {key: value for key, value in identity.items() if key not in ("card_id",)}
    return {"access_token": token, "user": user, "session": session}


def finish_session_service(session_id, actor_user_id, actor_role, terminate=False):
    positive_id(session_id, "session_id")
    return finish_session_repo(session_id, actor_user_id, actor_role, terminate)


def heartbeat_session_service(session_id, actor_user_id, token_session_id):
    positive_id(session_id, "session_id")
    if token_session_id != session_id:
        raise DomainError("Workstation session token is required.", 403)
    return heartbeat_session_repo(session_id, actor_user_id)


def session_history_service(actor_user_id, actor_role, active_only=False):
    if actor_role not in ("Admin", "Student"):
        raise DomainError("Access denied.", 403)
    return session_history_repo(actor_user_id, actor_role, active_only)


def recovery_candidates_service(minutes):
    if type(minutes) is not int or minutes < 1 or minutes > 10080:
        raise DomainError("minutes must be between 1 and 10080.")
    return recovery_candidates_repo(minutes)


def usage_summary_service():
    return usage_summary_repo()
