from flask import request
from pymysql.err import IntegrityError

from backend.services.rfid_service import (
    list_cards_service, register_card_service, assign_card_service,
    replace_card_service, set_card_status_service, card_history_service,
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
    except IntegrityError as exc:
        if exc.args[0] == 1062:
            return error("RFID card UID already exists.", 409)
        return error("RFID operation violates a database constraint.", 409)
    except Exception:
        return error("RFID operation failed.", 500)


def list_cards_control():
    return _run(list_cards_service, "RFID cards retrieved.")


def register_card_control():
    return _run(lambda: register_card_service(_body().get("card_uid")), "RFID card registered.", 201)


def assign_card_control(card_id):
    return _run(lambda: assign_card_service(card_id, _body().get("student_id")), "RFID card assigned.", 201)


def replace_card_control():
    def action():
        body = _body()
        return replace_card_service(body.get("student_id"), body.get("old_card_id"), body.get("new_card_id"))
    return _run(action, "RFID card replaced.")


def set_card_status_control(card_id):
    return _run(lambda: set_card_status_service(card_id, _body().get("status")), "RFID card status updated.")


def card_history_control(card_id):
    return _run(lambda: card_history_service(card_id), "RFID assignment history retrieved.")
