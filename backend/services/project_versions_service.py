"""Create and list versions; previous physical contents are kept."""
import os
from pathlib import Path
from uuid import uuid4

from flask import current_app

from backend.repositories import folders_repository as folders_repo
from backend.repositories import project_versions_repository as repo
from backend.database.connection import get_connection
from backend.services.folders_service import student_transaction, validate_name
from backend.utils.folder_errors import FolderError


def version_data(row):
    result = dict(row)
    value = result.get("created_at")
    if value is not None and hasattr(value, "isoformat"):
        # insert_version_repo stores this DATETIME explicitly in UTC.
        result["created_at"] = value.isoformat() + "Z"
    return result


def current_file_data(row):
    # Do not expose the server storage path.
    result = {
        key: row[key]
        for key in (
            "id", "project_id", "folder_id", "file_name",
            "file_type", "file_size", "created_at", "updated_at", "status"
        )
    }
    result["name"] = row["file_name"]
    for key in ("created_at", "updated_at"):
        value = result.get(key)
        if value is not None and hasattr(value, "isoformat"):
            result[key] = value.isoformat()
    return result


def cleanup_uncommitted_files(paths):
    """Delete new files only when a fresh DB read proves they were not committed."""
    for path in paths:
        try:
            if not repo.stored_path_is_referenced_repo(path):
                path.unlink(missing_ok=True)
        except Exception:
            # Keep uncertain bytes: deleting a committed version would be worse.
            current_app.logger.error("Project file cleanup requires storage reconciliation")


def read_file_version_service(version_id):
    """Internal-only historical content reader; caller must authorize the version first.

    Member 3 should authorize the submission and its pinned version before calling.
    No route exposes this operation directly.
    """
    if type(version_id) is not int or version_id < 1:
        raise FolderError("version_id must be a positive integer.", 400)

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            version = repo.get_stored_version_repo(cursor, version_id)
    finally:
        connection.close()
    if version is None:
        raise FolderError("File version not found.", 404)

    root = (Path(current_app.instance_path) / "project_uploads").resolve()
    try:
        path = Path(version["file_path"]).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise FolderError("Stored file version is unavailable.", 409)
        content = path.read_bytes()
    except OSError:
        raise FolderError("Stored file version is unavailable.", 409)
    if len(content) != version["file_size"]:
        raise FolderError("Stored file version is incomplete.", 409)
    return {
        "version_id": version["id"],
        "file_id": version["file_id"],
        "version_number": version["version_number"],
        "file_name": version["file_name"],
        "file_size": version["file_size"],
        "content": content,
    }


def checked_file(cursor, student_id, folder_id, project_id, file_id):
    folder, _ = folders_repo.get_active_folder_repo(
        cursor, student_id, folder_id
    )
    if folders_repo.root_key(folder) != "PROJECT":
        raise FolderError("Project root not found.", 404)

    row = repo.get_owned_file_repo(
        cursor, student_id, folder_id, project_id, file_id
    )
    if row is None:
        raise FolderError("File not found.", 404)
    return row


def list_file_versions_service(
    user_id, folder_id, project_id, file_id, limit=100, offset=0
):
    with student_transaction(user_id) as (cursor, student_id):
        file = checked_file(
            cursor, student_id, folder_id, project_id, file_id
        )
        rows = repo.list_versions_repo(cursor, file_id, limit, offset)
        return {
            "file": current_file_data(file),
            "versions": [version_data(row) for row in rows[:limit]],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(rows) > limit,
            },
        }


def upload_file_version_service(
    user_id, folder_id, project_id, file_id, uploaded
):
    if uploaded is None or not uploaded.filename:
        raise FolderError("Select an updated file to upload.", 400)

    # Validate the uploaded name, but keep the existing workspace file name.
    # File identity comes from file_id, never from a matching filename.
    validate_name(uploaded.filename, max_length=255)
    max_size = current_app.config.get(
        "PROJECT_FILE_MAX_BYTES", 20 * 1024 * 1024
    )
    saved_path = None

    try:
        with student_transaction(user_id) as (cursor, student_id):
            file = checked_file(
                cursor, student_id, folder_id, project_id, file_id
            )
            latest = repo.latest_version_number_repo(cursor, file_id)

            # Legacy files have no version history. Capture their CURRENT
            # contents as v1 before saving the replacement as v2.
            if latest == 0:
                old_path = Path(file["current_path"])
                if not old_path.is_file():
                    raise FolderError(
                        "Current file contents are missing; versioning cannot begin.",
                        409,
                    )
                old_size = old_path.stat().st_size
                baseline = repo.insert_version_repo(
                    cursor, file_id, 1, str(old_path), old_size, user_id
                )
                if baseline is None:
                    raise RuntimeError("Initial version could not be retrieved.")
                latest = 1

            directory = (
                Path(current_app.instance_path)
                / "project_uploads" / str(student_id) / str(project_id)
            )
            path = directory / uuid4().hex
            if len(str(path)) > 500:
                raise RuntimeError("Upload storage path is too long.")
            directory.mkdir(parents=True, exist_ok=True)

            file_size = 0
            with path.open("xb") as destination:
                saved_path = path
                while True:
                    chunk = uploaded.stream.read(64 * 1024)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > max_size:
                        raise FolderError(
                            "File exceeds the upload size limit.", 413
                        )
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())

            version = repo.insert_version_repo(
                cursor, file_id, latest + 1, str(path), file_size, user_id
            )
            if version is None:
                raise RuntimeError("New version could not be retrieved.")

            repo.update_current_file_repo(
                cursor, file_id, str(path), file_size,
                (uploaded.mimetype or "application/octet-stream")[:100],
            )
            updated_file = repo.get_owned_file_repo(
                cursor, student_id, folder_id, project_id, file_id
            )
            if updated_file is None:
                raise RuntimeError("Updated file could not be retrieved.")
            result = {
                "file": current_file_data(updated_file),
                "version": version_data(version),
            }

        return result

    except Exception:
        if saved_path is not None:
            cleanup_uncommitted_files([saved_path])
        raise
