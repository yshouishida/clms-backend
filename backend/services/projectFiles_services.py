from backend.repositories import folders_repository as folders_repo
from backend.repositories import projectFiles_repository as files_repo

from backend.services.folders_service import student_transaction
from backend.services.projects_services import project_data

from backend.utils.folder_errors import FolderError

from pathlib import Path
from uuid import uuid4

from flask import current_app

from backend.services.folders_service import validate_name


def file_data(row):
    result = dict(row)
    result["name"] = row["file_name"]

    for key in ("created_at", "updated_at"):
        value = result.get(key)

        if value is not None and hasattr(value, "isoformat"):
            result[key] = value.isoformat()

    return result


def list_project_files_service(
    user_id, folder_id, project_id, limit=100, offset=0
):
    with student_transaction(user_id) as (cursor, student_id):
        folder, _ = folders_repo.get_active_folder_repo(
            cursor,
            student_id,
            folder_id,
        )

        if folders_repo.root_key(folder) != "PROJECT":
            raise FolderError("Project root not found.", 404)

        project = files_repo.get_active_project_repo(
            cursor,
            student_id,
            folder_id,
            project_id,
        )

        if project is None:
            raise FolderError("Project not found.", 404)

        rows = files_repo.list_project_files_repo(
            cursor,
            project_id,
            limit,
            offset,
        )

        return {
            "project": project_data(project),
            "files": [
                file_data(row)
                for row in rows[:limit]
            ],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(rows) > limit,
            },
        }

def upload_project_files_service(
    user_id, folder_id, project_id, uploads
):
    max_files = current_app.config["PROJECT_UPLOAD_MAX_FILES"]
    max_file_size = current_app.config["PROJECT_FILE_MAX_BYTES"]
    max_total_size = current_app.config["PROJECT_UPLOAD_MAX_BYTES"]

    if not 1 <= len(uploads) <= max_files:
        raise FolderError(
            f"Send 1 to {max_files} files per upload.",
            400,
        )

    saved_paths = []
    results = []
    total_size = 0

    try:
        with student_transaction(user_id) as (cursor, student_id):
            folder, _ = folders_repo.get_active_folder_repo(
                cursor, student_id, folder_id
            )

            if folders_repo.root_key(folder) != "PROJECT":
                raise FolderError("Project root not found.", 404)

            project = files_repo.get_active_project_repo(
                cursor, student_id, folder_id, project_id
            )

            if project is None:
                raise FolderError("Project not found.", 404)

            directory = (
                Path(current_app.instance_path)
                / "project_uploads"
                / str(student_id)
                / str(project_id)
            )

            for uploaded in uploads:
                if uploaded is None or not uploaded.filename:
                    raise FolderError(
                        "Select a file to upload.",
                        400,
                    )

                file_name, _ = validate_name(
                    uploaded.filename,
                    max_length=255,
                )

                if files_repo.file_name_exists_repo(
                    cursor, project_id, file_name
                ):
                    raise FolderError(
                        f"A file named {file_name} already exists here.",
                        409,
                    )

                path = directory / uuid4().hex

                if len(str(path)) > 500:
                    raise RuntimeError(
                        "Upload storage path is too long."
                    )

                directory.mkdir(parents=True, exist_ok=True)
                file_size = 0

                with path.open("xb") as destination:
                    saved_paths.append(path)

                    while True:
                        chunk = uploaded.stream.read(64 * 1024)

                        if not chunk:
                            break

                        file_size += len(chunk)
                        total_size += len(chunk)

                        if file_size > max_file_size:
                            raise FolderError(
                                f"{file_name} exceeds the file size limit.",
                                413,
                            )

                        if total_size > max_total_size:
                            raise FolderError(
                                "Combined files exceed the upload size limit.",
                                413,
                            )

                        destination.write(chunk)

                row = files_repo.insert_project_file_repo(
                    cursor,
                    project_id,
                    folder_id,
                    file_name,
                    (
                        uploaded.mimetype
                        or "application/octet-stream"
                    )[:100],
                    file_size,
                    str(path),
                )

                if row is None:
                    raise RuntimeError(
                        "Uploaded file could not be retrieved."
                    )

                results.append(file_data(row))

        return {
            "files": results,
            "count": len(results),
        }

    except Exception:
        for path in saved_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Could not remove a failed upload"
                )

        raise

def _safe_project_storage_path(path_value):
    if not path_value:
        raise FolderError("Stored file path is missing.", 409)
    root = (Path(current_app.instance_path) / "project_uploads").resolve()
    candidate = Path(path_value).resolve()
    if not candidate.is_relative_to(root):
        raise FolderError("Stored file path is outside project storage.", 409)

    return candidate

def _check_owned_project_file(cursor, student_id, folder_id, project_id, file_id):
    folder, _ = folders_repo.get_active_folder_repo(
        cursor, student_id, folder_id
    )
    if folders_repo.root_key(folder) != "PROJECT":
        raise FolderError("Project root not found.", 404)

    project = files_repo.get_active_project_repo(
        cursor, student_id, folder_id, project_id
    )
    if project is None:
        raise FolderError("Project not found.", 404)

    file_row = files_repo.get_owned_project_file_repo(
        cursor, student_id, folder_id, project_id, file_id
    )
    if file_row is None:
        raise FolderError("File not found.", 404)

    return file_row

def download_project_file_service(user_id, folder_id, project_id, file_id):
    with student_transaction(user_id) as (cursor, student_id):
        row = _check_owned_project_file(
            cursor, student_id, folder_id, project_id, file_id
        )
        path = _safe_project_storage_path(row["current_path"])
        if not path.is_file():
            raise FolderError("Stored file contents are missing.", 409)
        return {
            "path": str(path),
            "file_name": row["file_name"],
            "file_type": row["file_type"] or "application/octet-stream",
        }

def rename_project_file_service(
    user_id, folder_id, project_id, file_id, new_file_name
):
    new_file_name, _ = validate_name(new_file_name, max_length=255)
    with student_transaction(user_id) as (cursor, student_id):
        row = _check_owned_project_file(
            cursor, student_id, folder_id, project_id, file_id
        )
        if files_repo.file_name_exists_excluding_repo(
            cursor, project_id, new_file_name, file_id
        ):
            raise FolderError(
                "A file with that name already exists in this project.", 409
            )
        updated = files_repo.rename_project_file_repo(
            cursor, project_id, file_id, new_file_name
        )
        if updated is None:
            raise FolderError("File could not be renamed.", 409)
        return file_data(updated)

def delete_project_file_service(user_id, folder_id, project_id, file_id):
    with student_transaction(user_id) as (cursor, student_id):
        _check_owned_project_file(
            cursor, student_id, folder_id, project_id, file_id
        )
        cursor.execute("SELECT UTC_TIMESTAMP() AS deleted_at")
        deleted_at = cursor.fetchone()["deleted_at"]
        result = files_repo.soft_delete_project_file_repo(
            cursor, project_id, file_id, deleted_at
        )
        payload = file_data(result)
        payload["deleted_at"] = (
            deleted_at.isoformat() + "Z"
            if hasattr(deleted_at, "isoformat")

            else str(deleted_at)
        )
        return payload