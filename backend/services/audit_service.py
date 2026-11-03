from backend.services.activities_service import activities_transaction, _profile_id
from backend.repositories import audit_repository
from backend.utils.domain_error import DomainError


def list_audit_events_service(
    user_id, role, limit, offset, filter_user_id=None, entity_name=None, action=None
):
    if role != "Admin":
        raise DomainError("Only Admins can access audit history.", 403)
    with activities_transaction() as cursor:
        _profile_id(cursor, user_id, role)
        return {
            "events": audit_repository.list_audit_events_repo(
                cursor, limit, offset, filter_user_id, entity_name, action
            ),
            "limit": limit,
            "offset": offset,
        }
