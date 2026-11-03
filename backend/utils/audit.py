from backend.repositories.audit_repository import insert_audit_event_repo


def record_audit_event(
    cursor,
    user_id,
    action,
    entity_name,
    record_id=None,
    description=None,
    ip_address=None,
):
    if not isinstance(action, str) or not action.strip():
        raise ValueError("Audit action is required.")
    if not isinstance(entity_name, str) or not entity_name.strip():
        raise ValueError("Audit entity name is required.")
    return insert_audit_event_repo(
        cursor,
        user_id,
        action.strip(),
        entity_name.strip(),
        record_id,
        description,
        ip_address,
    )
