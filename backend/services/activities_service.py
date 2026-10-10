from contextlib import contextmanager
from datetime import datetime, timezone

from backend.database.connection import get_connection
from backend.repositories import activities_repository as repo
from backend.repositories import classes_repository as classes_repo


class ActivitiesError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


@contextmanager
def activities_transaction():
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


def _profile_id(cursor, user_id, role):
    if role == "Instructor":
        profile = classes_repo.get_instructor_profile_repo(cursor, user_id)
        key = "instructor_id"
    elif role == "Student":
        profile = classes_repo.get_student_profile_repo(cursor, user_id)
        key = "student_id"
    else:
        return None
    if profile is None:
        raise ActivitiesError("An active account profile is required.", 403)
    return profile[key]


def _activity_fields(activity_name, instructions, due_date):
    if not isinstance(activity_name, str) or not activity_name.strip():
        raise ActivitiesError("activity_name is required and must be text.")
    activity_name = activity_name.strip()
    if len(activity_name) > 150:
        raise ActivitiesError("activity_name must not exceed 150 characters.")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ActivitiesError("instructions are required and must be text.")
    if len(instructions) > 65535:
        raise ActivitiesError("instructions are too long.")
    if not isinstance(due_date, str):
        raise ActivitiesError("due_date must be an ISO-8601 datetime string.")
    try:
        parsed_due_date = datetime.fromisoformat(
            due_date.strip().replace("Z", "+00:00")
        )
    except ValueError:
        raise ActivitiesError("due_date must be a valid ISO-8601 datetime.")
    if parsed_due_date.tzinfo is not None:
        parsed_due_date = parsed_due_date.astimezone(timezone.utc).replace(
            tzinfo=None
        )
    return {
        "activity_name": activity_name,
        "instructions": instructions.strip(),
        "due_date": parsed_due_date,
    }


def _serialize(row):
    if row is None:
        return None
    result = dict(row)
    for key in ("due_date", "created_at"):
        value = result.get(key)
        if value is not None and hasattr(value, "isoformat"):
            result[key] = value.isoformat()
    return result


def _get_class_for_role(cursor, class_id, role, profile_id):
    row = classes_repo.get_class_repo(cursor, class_id, role, profile_id)
    if row is None:
        raise ActivitiesError("Class not found.", 404)
    return row


def list_activities_service(user_id, role, class_id):
    if type(class_id) is not int or class_id < 1:
        raise ActivitiesError("class_id must be a positive integer.")
    with activities_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        _get_class_for_role(cursor, class_id, role, profile_id)
        rows = repo.list_activities_repo(cursor, class_id, role, profile_id)
        return [_serialize(row) for row in rows]


def get_activity_service(user_id, role, activity_id):
    if type(activity_id) is not int or activity_id < 1:
        raise ActivitiesError("activity_id must be a positive integer.")
    with activities_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        row = repo.get_activity_repo(cursor, activity_id, role, profile_id)
        if row is None:
            raise ActivitiesError("Activity not found.", 404)
        return _serialize(row)


def create_activity_service(
    user_id, role, class_id, activity_name, instructions, due_date
):
    if type(class_id) is not int or class_id < 1:
        raise ActivitiesError("class_id must be a positive integer.")
    if role != "Instructor":
        raise ActivitiesError("Only instructors can create activities.", 403)
    fields = _activity_fields(activity_name, instructions, due_date)

    with activities_transaction() as cursor:
        instructor_id = _profile_id(cursor, user_id, role)
        class_row = _get_class_for_role(
            cursor, class_id, role, instructor_id
        )
        if class_row["status"] != "Active":
            raise ActivitiesError(
                "Activities cannot be added to an archived class.", 409
            )
        activity_id = repo.insert_activity_repo(
            cursor, class_id, instructor_id, fields
        )
        row = repo.get_activity_repo(
            cursor, activity_id, role, instructor_id
        )
        if row is None:
            raise RuntimeError("Created activity could not be retrieved.")
        return _serialize(row)


def update_activity_service(
    user_id, role, activity_id, activity_name, instructions, due_date
):
    if type(activity_id) is not int or activity_id < 1:
        raise ActivitiesError("activity_id must be a positive integer.")
    if role not in ("Admin", "Instructor"):
        raise ActivitiesError("Access denied.", 403)
    fields = _activity_fields(activity_name, instructions, due_date)

    with activities_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        current = repo.get_activity_repo(
            cursor, activity_id, role, profile_id
        )
        if current is None:
            raise ActivitiesError("Activity not found.", 404)
        if current["status"] not in ("Draft", "Published"):
            raise ActivitiesError(
                "Closed or archived activities cannot be edited.", 409
            )
        repo.update_activity_repo(cursor, activity_id, fields)
        return _serialize(
            repo.get_activity_repo(cursor, activity_id, role, profile_id)
        )


def update_activity_status_service(user_id, role, activity_id, status):
    if type(activity_id) is not int or activity_id < 1:
        raise ActivitiesError("activity_id must be a positive integer.")
    if role not in ("Admin", "Instructor"):
        raise ActivitiesError("Access denied.", 403)
    if status not in ("Draft", "Published", "Closed", "Archived"):
        raise ActivitiesError("status is invalid.")

    transitions = {
        "Draft": {"Published", "Archived"},
        "Published": {"Closed", "Archived"},
        "Closed": {"Archived"},
        "Archived": set(),
    }
    with activities_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        current = repo.get_activity_repo(
            cursor, activity_id, role, profile_id
        )
        if current is None:
            raise ActivitiesError("Activity not found.", 404)
        if status == current["status"]:
            return _serialize(current)
        if status not in transitions[current["status"]]:
            raise ActivitiesError(
                f"Cannot change activity from {current['status']} to {status}.",
                409,
            )
        repo.update_activity_status_repo(cursor, activity_id, status)
        return _serialize(
            repo.get_activity_repo(cursor, activity_id, role, profile_id)
        )