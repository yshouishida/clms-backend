from contextlib import contextmanager

from backend.database.connection import get_connection
from backend.repositories import inventory_repository
from backend.repositories import issues_repository as repo
from backend.repositories import classes_repository
from backend.utils.audit import record_audit_event
from backend.utils.domain_error import DomainError


@contextmanager
def issues_transaction():
    connection = get_connection()
    try:
        connection.begin()
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def issue_fields(body):
    allowed = {"issue_type", "title", "description", "priority", "session_id"}
    required = {"issue_type", "title", "description"}
    if not isinstance(body, dict) or required - set(body) or set(body) - allowed:
        raise DomainError(
            "Send issue_type, title, description, optional priority, and optional session_id."
        )
    issue_type = body["issue_type"]
    title = body["title"]
    description = body["description"]
    priority = body.get("priority", "Medium")
    session_id = body.get("session_id")
    if issue_type not in (
        "Hardware", "Software", "Network", "Camera", "RFID Reader", "Other"
    ):
        raise DomainError("Invalid issue_type.")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 150:
        raise DomainError("title is required and must not exceed 150 characters.")
    try:
        title.strip().encode("utf-8")
    except UnicodeEncodeError:
        raise DomainError("title must contain valid text.")
    if not isinstance(description, str) or not description.strip():
        raise DomainError("description is required.")
    try:
        description_size = len(description.encode("utf-8"))
    except UnicodeEncodeError:
        raise DomainError("description must contain valid text.")
    if description_size > 65535:
        raise DomainError("description is too long.")
    if priority not in ("Low", "Medium", "High", "Critical"):
        raise DomainError("priority must be Low, Medium, High, or Critical.")
    if session_id is not None and (type(session_id) is not int or session_id < 1):
        raise DomainError("session_id must be a positive integer or null.")
    return {
        "issue_type": issue_type,
        "title": title.strip(),
        "description": description.strip(),
        "priority": priority,
        "session_id": session_id,
    }


def report_issue_service(user_id, role, workstation_id, body):
    if role not in ("Admin", "Instructor", "Student"):
        raise DomainError("Access denied.", 403)
    if type(workstation_id) is not int or workstation_id < 1:
        raise DomainError("workstation_id must be a positive integer.")
    fields = issue_fields(body)
    with issues_transaction() as cursor:
        workstation = inventory_repository.get_inventory_repo(
            cursor, "workstations", workstation_id, lock=True
        )
        if workstation is None:
            raise DomainError("Workstation not found.", 404)
        if workstation["status"] == "Retired":
            raise DomainError("Issues cannot be reported for a retired workstation.", 409)
        if fields["session_id"] is not None:
            session = repo.session_workstation_repo(
                cursor, fields["session_id"], workstation_id
            )
            if session is None:
                raise DomainError(
                    "session_id must belong to the reported workstation.", 400
                )
            if role == "Student":
                profile = classes_repository.get_student_profile_repo(
                    cursor, user_id
                )
                if profile is None or session["student_id"] != profile["student_id"]:
                    raise DomainError(
                        "Students can report issues only for their own sessions.",
                        403,
                    )
        issue_id = repo.insert_issue_repo(
            cursor, workstation_id, user_id, fields["session_id"], fields
        )
        record_audit_event(
            cursor, user_id, "Report", "Issue Report", issue_id,
            f"Reported {fields['priority']} {fields['issue_type']} issue "
            f"for workstation {workstation_id}.",
        )
        return repo.issue_repo(cursor, issue_id)


def list_issues_service(
    role, user_id, limit=100, offset=0, workstation_id=None, status=None
):
    if role not in ("Admin", "Instructor", "Student"):
        raise DomainError("Access denied.", 403)
    if role == "Student":
        rows_user_id = user_id
    else:
        rows_user_id = None
    if status is not None and status not in (
        "Pending", "Under Review", "In Progress", "Resolved", "Closed", "Rejected"
    ):
        raise DomainError("Invalid issue status.")
    with issues_transaction() as cursor:
        rows = repo.list_issues_repo(
            cursor, limit, offset, rows_user_id, workstation_id, status
        )
        return {"issues": rows, "limit": limit, "offset": offset}


def update_issue_service(user_id, role, issue_id, status, resolution_details):
    if role not in ("Admin", "Instructor"):
        raise DomainError("Only instructors and Admins can update PC issues.", 403)
    if type(issue_id) is not int or issue_id < 1:
        raise DomainError("issue_id must be a positive integer.")
    if status not in (
        "Pending", "Under Review", "In Progress", "Resolved", "Closed", "Rejected"
    ):
        raise DomainError("Invalid issue status.")
    if resolution_details is not None:
        if not isinstance(resolution_details, str):
            raise DomainError("resolution_details must be text.")
        try:
            resolution_size = len(resolution_details.encode("utf-8"))
        except UnicodeEncodeError:
            raise DomainError("resolution_details must contain valid text.")
        if resolution_size > 65535:
            raise DomainError("resolution_details is too long.")
        resolution_details = resolution_details.strip() or None

    transitions = {
        "Pending": {"Under Review", "In Progress", "Resolved", "Rejected"},
        "Under Review": {"In Progress", "Resolved", "Rejected"},
        "In Progress": {"Resolved", "Rejected"},
        "Resolved": {"Closed", "In Progress"},
        "Rejected": {"Under Review"},
        "Closed": set(),
    }
    with issues_transaction() as cursor:
        issue = repo.issue_repo(cursor, issue_id, lock=True)
        if issue is None:
            raise DomainError("Issue not found.", 404)
        if status != issue["status"] and status not in transitions[issue["status"]]:
            raise DomainError(
                f"Cannot change issue from {issue['status']} to {status}.", 409
            )
        if status in ("Resolved", "Rejected") and not resolution_details and not issue[
            "resolution_details"
        ]:
            raise DomainError(
                "resolution_details is required to resolve or reject an issue."
            )
        if status in ("Pending", "Under Review", "In Progress"):
            final_resolution = resolution_details
        else:
            final_resolution = (
                resolution_details
                if resolution_details is not None
                else issue["resolution_details"]
            )
        resolved_by = (
            user_id if status == "Resolved"
            else issue["resolved_by"] if status == "Closed"
            else None
        )
        repo.update_issue_repo(
            cursor, issue_id, status, final_resolution, resolved_by
        )
        record_audit_event(
            cursor, user_id, "Status Change", "Issue Report", issue_id,
            f"Changed issue status from {issue['status']} to {status}.",
        )
        return repo.issue_repo(cursor, issue_id)
