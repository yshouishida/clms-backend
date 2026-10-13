from flask import Blueprint

from backend.controllers.rfid_controller import (
    list_cards_control, register_card_control, assign_card_control,
    replace_card_control, set_card_status_control, card_history_control,
)
from backend.utils.jwt import token_required, role_required

rfid_bp = Blueprint("rfid", __name__)


@rfid_bp.get("/rfid/cards")
@token_required
@role_required("Admin")
def list_cards():
    return list_cards_control()


@rfid_bp.post("/rfid/cards")
@token_required
@role_required("Admin")
def register_card():
    return register_card_control()


@rfid_bp.post("/rfid/cards/<int:card_id>/assignments")
@token_required
@role_required("Admin")
def assign_card(card_id):
    return assign_card_control(card_id)


@rfid_bp.post("/rfid/cards/replacement")
@token_required
@role_required("Admin")
def replace_card():
    return replace_card_control()


@rfid_bp.patch("/rfid/cards/<int:card_id>/status")
@token_required
@role_required("Admin")
def set_card_status(card_id):
    return set_card_status_control(card_id)


@rfid_bp.get("/rfid/cards/<int:card_id>/assignments")
@token_required
@role_required("Admin")
def card_history(card_id):
    return card_history_control(card_id)
