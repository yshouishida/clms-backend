from backend.repositories import announcements_repository as repo
from backend.services.classes_service import (
    ClassesError,
    _profile_id,
    classes_transaction,
)
from backend.repositories import classes_repository
from backend.utils.audit import record_audit_event


def _serialize(row):
    result = dict(row)
    if result.get("posted_at") is not None:
        result["posted_at"] = result["posted_at"].isoformat()
    return result


def _announcement_fields(title, content):
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 150:
        raise ClassesError("title is required and must not exceed 150 characters.")
    if not isinstance(content, str) or not content.strip():
        raise ClassesError("content is required.")
    try:
        if len(content.encode("utf-8")) > 65535:
            raise ClassesError("content is too long.")
    except UnicodeEncodeError:
        raise ClassesError("content must contain valid text.")
    return title.strip(), content.strip()


def list_announcements_service(user_id, role, class_id):
    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        class_row = classes_repository.get_class_repo(
            cursor, class_id, role, profile_id
        )
        if class_row is None:
            raise ClassesError("Class not found.", 404)
        rows = repo.list_announcements_repo(
            cursor, class_id, role in ("Instructor", "Admin")
        )
        return [_serialize(row) for row in rows]


def create_announcement_service(user_id, role, class_id, title, content):
    if role not in ("Instructor", "Admin"):
        raise ClassesError("Only instructors and Admins can post announcements.", 403)
    title, content = _announcement_fields(title, content)
    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        class_row = classes_repository.get_class_repo(
            cursor, class_id, role, profile_id
        )
        if class_row is None:
            raise ClassesError("Class not found.", 404)
        if class_row["status"] != "Active":
            raise ClassesError("Cannot post to an archived class.", 409)
        announcement_id = repo.insert_announcement_repo(
            cursor, class_id, user_id, title, content
        )
        record_audit_event(
            cursor, user_id, "Create", "Announcement", announcement_id,
            f"Posted an announcement to class {class_id}.",
        )
        result = repo.announcement_detail_repo(cursor, announcement_id)
        return _serialize(result)


def update_announcement_service(
    user_id, role, announcement_id, title, content, status
):
    if type(announcement_id) is not int or announcement_id < 1:
        raise ClassesError("announcement_id must be a positive integer.")
    if role not in ("Instructor", "Admin"):
        raise ClassesError("Only instructors and Admins can update announcements.", 403)
    if status not in ("Published", "Archived"):
        raise ClassesError("status must be Published or Archived.")
    title, content = _announcement_fields(title, content)
    with classes_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        announcement = repo.announcement_class_repo(cursor, announcement_id, True)
        if announcement is None:
            raise ClassesError("Announcement not found.", 404)
        if classes_repository.get_class_repo(
            cursor, announcement["class_id"], role, profile_id
        ) is None:
            raise ClassesError("Announcement not found.", 404)
        repo.update_announcement_repo(
            cursor, announcement_id, title, content, status
        )
        record_audit_event(
            cursor, user_id, "Update", "Announcement", announcement_id,
            f"Updated announcement; status is {status}.",
        )
        updated = repo.announcement_detail_repo(cursor, announcement_id)
        return _serialize(updated)
