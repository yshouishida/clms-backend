from contextlib import contextmanager
import re
import unicodedata

from backend.database.connection import get_connection
from backend.repositories import folders_repository as repo
from backend.utils.folder_errors import FolderError


ROOTS = (
    ("PROJECT", "Project"),
    ("ACTIVITIES", "Activities"),
)

INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')

RESERVED_NAMES = {"con", "prn", "aux", "nul"} | {
    f"{prefix}{n}"
    for prefix in ("com", "lpt")
    for n in range(1, 10)
}


def validate_name(name):
    if not isinstance(name, str):
        raise FolderError("name must be a string.", 400)

    name = unicodedata.normalize("NFC", name).strip()

    if not name or len(name) > 100:
        raise FolderError(
            "name must contain 1 to 100 characters.",
            400,
        )

    if (
        name in (".", "..")
        or INVALID_NAME.search(name)
        or name.endswith(".")
    ):
        raise FolderError(
            "name contains an invalid folder name or character.",
            400,
        )

    if name.split(".", 1)[0].casefold() in RESERVED_NAMES:
        raise FolderError("name is reserved by Windows.", 400)

    if any(unicodedata.category(c) in ("Cs", "Cf") for c in name):
        raise FolderError(
            "name contains unsupported control characters.",
            400,
        )

    return name, repo.name_key(name)


def folder_data(row):
    result = dict(row)

    # Keep "name" available to the desktop application.
    result["name"] = row["folder_name"]

    # These are calculated response fields, not database columns.
    result["root_key"] = repo.root_key(row)
    result["is_system_root"] = result["root_key"] is not None

    for key in ("created_at", "deleted_at"):
        value = result.get(key)

        if value is not None and hasattr(value, "isoformat"):
            result[key] = value.isoformat()

    return result


@contextmanager
def student_transaction(user_id):
    if type(user_id) is not int or user_id < 1:
        raise FolderError("Authentication is required.", 401)

    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            student_id = repo.require_active_student_repo(
                cursor,
                user_id,
            )

            yield cursor, student_id

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def checked_roots(cursor, student_id):
    roots = {}

    for row in repo.list_roots_repo(cursor, student_id):
        key = repo.root_key(row)

        if key is None:
            continue

        if (
            key in roots
            or row["status"] != "Active"
            or row["deleted_at"] is not None
        ):
            raise FolderError(
                "Workspace roots need administrator repair.",
                409,
            )

        roots[key] = row

    return roots


def initialize_roots_service(user_id):
    with student_transaction(user_id) as (cursor, student_id):
        existing = checked_roots(cursor, student_id)

        for key, name in ROOTS:
            if key not in existing:
                repo.insert_root_repo(cursor, student_id, name)

        existing = checked_roots(cursor, student_id)

        return [
            folder_data(existing[key])
            for key, _ in ROOTS
        ]


def list_roots_service(user_id):
    with student_transaction(user_id) as (cursor, student_id):
        existing = checked_roots(cursor, student_id)

        return [
            folder_data(existing[key])
            for key, _ in ROOTS
            if key in existing
        ]


def open_folder_service(user_id, folder_id, limit=100, offset=0):
    with student_transaction(user_id) as (cursor, student_id):
        folder, _ = repo.get_active_folder_repo(
            cursor,
            student_id,
            folder_id,
        )

        children = repo.list_children_repo(
            cursor,
            student_id,
            folder_id,
            limit,
            offset,
        )

        return {
            "folder": folder_data(folder),
            "folders": [
                folder_data(row)
                for row in children[:limit]
            ],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(children) > limit,
            },
        }


def create_folder_service(user_id, parent_folder_id, name):
    if type(parent_folder_id) is not int or parent_folder_id < 1:
        raise FolderError(
            "parent_folder_id must be a positive integer.",
            400,
        )

    name, normalized_name = validate_name(name)

    with student_transaction(user_id) as (cursor, student_id):
        _, depth = repo.get_active_folder_repo(
            cursor,
            student_id,
            parent_folder_id,
        )

        if depth >= repo.MAX_FOLDER_DEPTH:
            raise FolderError(
                "The maximum folder depth has been reached.",
                400,
            )

        if repo.sibling_name_exists_repo(
            cursor,
            student_id,
            parent_folder_id,
            normalized_name,
        ):
            raise FolderError(
                "A folder with that name already exists here.",
                409,
            )

        folder_id = repo.insert_folder_repo(
            cursor,
            student_id,
            parent_folder_id,
            name,
        )

        row, _ = repo.get_active_folder_repo(
            cursor,
            student_id,
            folder_id,
        )

        return folder_data(row)