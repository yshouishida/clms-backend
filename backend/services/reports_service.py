from backend.services.activities_service import activities_transaction, _profile_id
from backend.repositories import activities_repository
from backend.repositories import classes_repository
from backend.repositories import reports_repository
from backend.utils.domain_error import DomainError


def _authorized_class(cursor, user_id, role, class_id):
    if role not in ("Admin", "Instructor", "Student"):
        raise DomainError("Access denied.", 403)
    profile_id = _profile_id(cursor, user_id, role)
    row = classes_repository.get_class_repo(cursor, class_id, role, profile_id)
    if row is None:
        raise DomainError("Class not found.", 404)
    return profile_id


def activities_report_service(user_id, role, class_id):
    if role == "Student":
        raise DomainError("Only instructors and Admins can view activity reports.", 403)
    with activities_transaction() as cursor:
        _authorized_class(cursor, user_id, role, class_id)
        return reports_repository.activity_report_repo(cursor, class_id)


def submissions_report_service(user_id, role, class_id, activity_id=None):
    if role == "Student":
        raise DomainError("Only instructors and Admins can view submission reports.", 403)
    with activities_transaction() as cursor:
        _authorized_class(cursor, user_id, role, class_id)
        if activity_id is not None:
            activity = activities_repository.get_activity_repo(
                cursor, activity_id, role,
                _profile_id(cursor, user_id, role),
            )
            if activity is None or activity["class_id"] != class_id:
                raise DomainError("Activity not found.", 404)
        return reports_repository.submission_report_repo(
            cursor, class_id, activity_id
        )


def student_progress_report_service(user_id, role, class_id, student_id=None):
    with activities_transaction() as cursor:
        profile_id = _authorized_class(cursor, user_id, role, class_id)
        if role == "Student":
            if student_id is not None and student_id != profile_id:
                raise DomainError("Students can view only their own progress.", 403)
            student_id = profile_id
        rows = reports_repository.student_progress_report_repo(
            cursor, class_id, student_id
        )
        if student_id is not None and not rows:
            raise DomainError("Enrolled student not found.", 404)
        return rows
