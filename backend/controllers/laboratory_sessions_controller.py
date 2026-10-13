from flask import g, request

from backend.services.laboratory_sessions_service import (
    verify_workstation_key_service, manual_workstation_login_service,
    rfid_workstation_login_service, finish_session_service,
    heartbeat_session_service,
    session_history_service, recovery_candidates_service, usage_summary_service,
)
from backend.utils.api_response import success, error
from backend.utils.domain_error import DomainError


def _body():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        raise DomainError("Request body must be a valid JSON object.")

    return body


def _run(action, message, status=200):
    try:
        return success(message, status, action())

    except DomainError as exc:
        return error(str(exc), exc.status_code)

    except Exception:
        return error("Laboratory session operation failed.", 500)


def manual_workstation_login_control():
    def action():
        verify_workstation_key_service(request.headers.get("X-Workstation-Key"))
        body = _body()

        return manual_workstation_login_service(
            body.get("username"),
            body.get("password"),
            body.get("workstation_id"),
            request.remote_addr
        )

    return _run(action, "Student workstation login succeeded.", 201)


def rfid_workstation_login_control():
    def action():
        verify_workstation_key_service(request.headers.get("X-Workstation-Key"))
        body = _body()

        return rfid_workstation_login_service(
            body.get("card_uid"),
            body.get("workstation_id"),
            body.get("reader_id"),
            request.remote_addr
        )

    return _run(action, "RFID workstation login succeeded.", 201)


def logout_session_control(session_id):
    return _run(
        lambda: finish_session_service(session_id, g.user_id, g.user_role),
        "Laboratory session completed."
    )


def heartbeat_session_control(session_id):
    return _run(
        lambda: heartbeat_session_service(
            session_id, g.user_id, g.jwt_payload.get("session_id")
        ),
        "Laboratory session heartbeat recorded.",
        201
    )


def terminate_session_control(session_id):
    return _run(
        lambda: finish_session_service(session_id, g.user_id, g.user_role, True),
        "Laboratory session terminated."
    )


def session_history_control(active_only=False):
    return _run(
        lambda: session_history_service(g.user_id, g.user_role, active_only),
        "Laboratory sessions retrieved."
    )


def recovery_candidates_control():
    def action():
        raw = request.args.get("minutes", "60")
        try:
            minutes = int(raw)

        except ValueError:
            raise DomainError("minutes must be an integer.")

        return recovery_candidates_service(minutes)

    return _run(action, "Active sessions requiring review retrieved.")


def usage_summary_control():
    return _run(usage_summary_service, "Session usage summary retrieved.")
