from backend.repositories.rfid_repository import (
    list_cards_repo, register_card_repo, assign_card_repo, replace_card_repo,
    set_card_status_repo, card_history_repo,
)
from backend.utils.domain_error import DomainError


def positive_id(value, name):
    if type(value) is not int or value < 1:
        raise DomainError(f"{name} must be a positive integer.")
    return value


def list_cards_service():
    return list_cards_repo()


def register_card_service(card_uid):
    if not isinstance(card_uid, str) or not card_uid.strip() or len(card_uid.strip()) > 100:
        raise DomainError("card_uid must be a nonempty string of at most 100 characters.")
    return register_card_repo(card_uid.strip())


def assign_card_service(card_id, student_id):
    return assign_card_repo(positive_id(card_id, "card_id"), positive_id(student_id, "student_id"))


def replace_card_service(student_id, old_card_id, new_card_id):
    positive_id(student_id, "student_id")
    positive_id(old_card_id, "old_card_id")
    positive_id(new_card_id, "new_card_id")
    if old_card_id == new_card_id:
        raise DomainError("Replacement card must differ from the old card.")
    return replace_card_repo(student_id, old_card_id, new_card_id)


def set_card_status_service(card_id, status):
    positive_id(card_id, "card_id")
    if status not in ("Active", "Inactive", "Disabled", "Lost", "Damaged"):
        raise DomainError("Invalid RFID card status.")
    return set_card_status_repo(card_id, status)


def card_history_service(card_id):
    return card_history_repo(positive_id(card_id, "card_id"))
