from backend.repositories import folders_repository as folders_repo
from backend.repositories import projects_repository as projects_repo

from backend.services.folders_service import (
    student_transaction,
    folder_data,
    validate_name,
)



from backend.utils.folder_errors import FolderError


def project_data(row):
    result = dict(row)
    result["name"] = row["project_name"]

    for key in ("created_at", "updated_at", "deleted_at"):
        value = result.get(key)

        if value is not None and hasattr(value, "isoformat"):
            result[key] = value.isoformat()

    return result


def list_folder_projects_service(
    user_id, folder_id, limit=100, offset=0
):
    with student_transaction(user_id) as (cursor, student_id):
        folder, _ = folders_repo.get_active_folder_repo(
            cursor,
            student_id,
            folder_id,
        )

        if folders_repo.root_key(folder) != "PROJECT":
            raise FolderError("Project root not found.", 404)

        rows = projects_repo.list_projects_in_folder_repo(
            cursor,
            student_id,
            folder_id,
            limit,
            offset,
        )

        return {
            "folder": folder_data(folder),
            "projects": [
                project_data(row)
                for row in rows[:limit]
            ],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(rows) > limit,
            },
        }


def create_folder_project_service(
    user_id, folder_id, project_name, description=None
):
    project_name, _ = validate_name(
        project_name,
        max_length=150,
    )

    if description is not None:
        if not isinstance(description, str):
            raise FolderError(
                "description must be text or null.",
                400,
            )

        try:
            description_size = len(description.encode("utf-8"))
        except UnicodeEncodeError:
            raise FolderError(
                "description contains unsupported characters.",
                400,
            )

        if description_size > 65535:
            raise FolderError("description is too long.", 400)

    with student_transaction(user_id) as (cursor, student_id):
        folder, _ = folders_repo.get_active_folder_repo(
            cursor,
            student_id,
            folder_id,
        )

        if folders_repo.root_key(folder) != "PROJECT":
            raise FolderError("Project root not found.", 404)

        if projects_repo.project_name_exists_repo(
            cursor,
            student_id,
            folder_id,
            project_name,
        ):
            raise FolderError(
                "A project with that name already exists here.",
                409,
            )

        row = projects_repo.insert_project_repo(
            cursor,
            student_id,
            folder_id,
            project_name,
            description,
        )

        if row is None:
            raise RuntimeError(
                "Created project could not be retrieved."
            )

        return project_data(row)