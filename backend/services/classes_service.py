from contextlib import contextmanager

from backend.database.connection import get_connection
from backend.repositories import classes_repository as repo


class ClassesError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


@contextmanager
def classes_transaction():
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
        profile = repo.get_instructor_profile_repo(cursor, user_id)
        key = "instructor_id"
    elif role == "Student":
        profile = repo.get_student_profile_repo(cursor, user_id)
        key = "student_id"
    else:
        return None

    if profile is None:
        raise ClassesError("An active account profile is required.", 403)
    return profile[key]


def _class_fields(class_code, class_name, school_year, semester, description):
    text_fields = {
        "class_code": (class_code, 30),
        "class_name": (class_name, 100),
        "school_year": (school_year, 20),
    }
    fields = {}

    for name, (value, maximum) in text_fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ClassesError(f"{name} is required and must be text.")
        value = value.strip()
        if len(value) > maximum:
            raise ClassesError(f"{name} must not exceed {maximum} characters.")
        fields[name] = value

    if semester not in ("First Semester", "Second Semester", "Summer"):
        raise ClassesError("semester is invalid.")

    if description is not None and not isinstance(description, str):
        raise ClassesError("description must be text or null.")
    if description is not None and len(description) > 65535:
        raise ClassesError("description is too long.")

    fields["semester"] = semester
    fields["description"] = description
    return fields


def _serialize(row):
    if row is None:
        return None
    result = dict(row)
    for key in ("created_at", "enrolled_at"):
        value = result.get(key)
        if value is not None and hasattr(value, "isoformat"):
            result[key] = value.isoformat()
    return result


def list_classes_service(user_id, role):
    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        rows = repo.list_classes_repo(cursor, role, profile_id)
        return [_serialize(row) for row in rows]


def get_class_service(user_id, role, class_id):
    if type(class_id) is not int or class_id < 1:
        raise ClassesError("class_id must be a positive integer.")
    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        row = repo.get_class_repo(cursor, class_id, role, profile_id)
        if row is None:
            raise ClassesError("Class not found.", 404)
        return _serialize(row)


def create_class_service(
    user_id, role, class_code, class_name, school_year, semester, description=None
):
    fields = _class_fields(
        class_code, class_name, school_year, semester, description
    )
    if role != "Instructor":
        raise ClassesError("Only instructors can create classes.", 403)

    with classes_transaction() as cursor:
        instructor_id = _profile_id(cursor, user_id, role)
        if repo.class_code_exists_repo(
            cursor,
            fields["class_code"],
            fields["school_year"],
            fields["semester"],
            instructor_id,
        ):
            raise ClassesError("This class code already exists for the term.", 409)

        class_id = repo.insert_class_repo(cursor, instructor_id, fields)
        row = repo.get_class_repo(cursor, class_id, role, instructor_id)
        if row is None:
            raise RuntimeError("Created class could not be retrieved.")
        return _serialize(row)


def update_class_service(
    user_id, role, class_id, class_code, class_name, school_year, semester,
    description=None,
):
    if type(class_id) is not int or class_id < 1:
        raise ClassesError("class_id must be a positive integer.")
    fields = _class_fields(
        class_code, class_name, school_year, semester, description
    )
    if role not in ("Admin", "Instructor"):
        raise ClassesError("Access denied.", 403)

    with classes_transaction() as cursor:
        instructor_id = _profile_id(cursor, user_id, role)
        existing = repo.get_class_repo(cursor, class_id, role, instructor_id)
        if existing is None:
            raise ClassesError("Class not found.", 404)
        owner_id = existing["instructor_id"]
        if repo.class_code_exists_repo(
            cursor,
            fields["class_code"],
            fields["school_year"],
            fields["semester"],
            owner_id,
            exclude_id=class_id,
        ):
            raise ClassesError("This class code already exists for the term.", 409)
        repo.update_class_repo(
            cursor, class_id, instructor_id, fields, role == "Admin"
        )
        return _serialize(
            repo.get_class_repo(cursor, class_id, role, instructor_id)
        )


def archive_class_service(user_id, role, class_id):
    if type(class_id) is not int or class_id < 1:
        raise ClassesError("class_id must be a positive integer.")
    if role not in ("Admin", "Instructor"):
        raise ClassesError("Access denied.", 403)

    with classes_transaction() as cursor:
        instructor_id = _profile_id(cursor, user_id, role)
        if not repo.archive_class_repo(
            cursor, class_id, instructor_id, role == "Admin"
        ):
            raise ClassesError("Class not found.", 404)
        return _serialize(repo.get_class_repo(cursor, class_id, role, instructor_id))


def list_class_members_service(user_id, role, class_id):
    if type(class_id) is not int or class_id < 1:
        raise ClassesError("class_id must be a positive integer.")
    if role not in ("Admin", "Instructor"):
        raise ClassesError("Access denied.", 403)

    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        if repo.get_class_repo(cursor, class_id, role, profile_id) is None:
            raise ClassesError("Class not found.", 404)
        return [
            _serialize(row)
            for row in repo.list_class_members_repo(cursor, class_id)
        ]


def enroll_student_service(user_id, role, class_id, student_id):
    if type(class_id) is not int or class_id < 1:
        raise ClassesError("class_id must be a positive integer.")
    if type(student_id) is not int or student_id < 1:
        raise ClassesError("student_id must be a positive integer.")
    if role not in ("Admin", "Instructor"):
        raise ClassesError("Access denied.", 403)

    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        class_row = repo.get_class_repo(cursor, class_id, role, profile_id)
        if class_row is None:
            raise ClassesError("Class not found.", 404)
        if class_row["status"] != "Active":
            raise ClassesError("Students cannot be enrolled in an archived class.", 409)
        if not repo.student_is_active_repo(cursor, student_id):
            raise ClassesError("Active student not found.", 404)

        member = repo.get_class_member_repo(cursor, class_id, student_id)
        if member is None:
            member_id = repo.insert_class_member_repo(
                cursor, class_id, student_id
            )
        elif member["status"] == "Dropped":
            repo.update_class_member_repo(
                cursor, class_id, student_id, "Enrolled"
            )
            member_id = member["id"]
        else:
            raise ClassesError("Student already has a class membership.", 409)

        result = repo.get_class_member_repo(cursor, class_id, student_id)
        if result is None:
            raise RuntimeError(f"Created class membership {member_id} was not found.")
        return _serialize(result)


def update_class_member_service(user_id, role, class_id, student_id, status):
    if type(class_id) is not int or class_id < 1:
        raise ClassesError("class_id must be a positive integer.")
    if type(student_id) is not int or student_id < 1:
        raise ClassesError("student_id must be a positive integer.")
    if status not in ("Enrolled", "Dropped", "Completed"):
        raise ClassesError("status is invalid.")
    if role not in ("Admin", "Instructor"):
        raise ClassesError("Access denied.", 403)

    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        if repo.get_class_repo(cursor, class_id, role, profile_id) is None:
            raise ClassesError("Class not found.", 404)
        member = repo.get_class_member_repo(cursor, class_id, student_id)
        if member is None:
            raise ClassesError("Class membership not found.", 404)
        if member["status"] == "Completed" and status != "Completed":
            raise ClassesError("Completed memberships cannot be reopened.", 409)
        repo.update_class_member_repo(cursor, class_id, student_id, status)
        return _serialize(
            repo.get_class_member_repo(cursor, class_id, student_id)
        )