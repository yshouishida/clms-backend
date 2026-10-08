"""Create and list versions; previous physical contents are kept."""
from pathlib import Path
from uuid import uuid4

from flask import current_app

from backend.repositories import folders_repository as folders_repo
from backend.repositories import project_versions_repository as repo
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
        # Only this request's NEW physical file is removed on failure.
        # Older versions and the legacy baseline stay untouched.
        if saved_path is not None:
            try:
                saved_path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Could not remove a failed version upload"
                )
        raise
