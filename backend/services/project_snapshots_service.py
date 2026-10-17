from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import shutil

from flask import current_app

from backend.repositories import folders_repository as folders_repo
from backend.repositories import projects_repository as projects_repo
from backend.repositories import projectFiles_repository as files_repo
from backend.repositories import project_versions_repository as versions_repo
from backend.services.folders_service import student_transaction, validate_name
from backend.utils.folder_errors import FolderError
from backend.utils.project_snapshot_storage import (
    SnapshotManifestError,
    list_snapshot_manifests,
    new_snapshot_id,
    normalize_snapshot_id,
    read_snapshot_manifest,
    write_snapshot_manifest,
)


def _storage_path(path_value):
    if not path_value:
        raise FolderError("Stored file path is missing.", 409)
    root = (Path(current_app.instance_path) / "project_uploads").resolve()
    candidate = Path(path_value).resolve()
    if not candidate.is_relative_to(root):
        raise FolderError("Stored version path is outside project storage.", 409)
    return candidate


def _sha256_file(path):
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _snapshot_data(manifest):
    return {
        "snapshot_id": manifest["snapshot_id"],
        "project_id": manifest["project_id"],
        "snapshot_name": manifest.get("snapshot_name"),
        "created_by": manifest["created_by"],
        "created_at": manifest["created_at"],
        "file_count": manifest["file_count"],
    }


def _check_active_project(cursor, student_id, folder_id, project_id):
    folder, _ = folders_repo.get_active_folder_repo(
        cursor, student_id, folder_id
    )
    if folders_repo.root_key(folder) != "PROJECT":
        raise FolderError("Project root not found.", 404)
    project = projects_repo.get_owned_project_repo(
        cursor, student_id, folder_id, project_id
    )
    if project is None:
        raise FolderError("Project not found.", 404)
    return project


def _validated_manifest_name(value, label, max_length):
    try:
        cleaned, _ = validate_name(value, max_length=max_length)
    except FolderError as exc:
        raise FolderError(f"Snapshot contains an invalid {label}.", 409) from exc
    if cleaned != value:
        raise FolderError(f"Snapshot contains a noncanonical {label}.", 409)
    return cleaned


def create_project_snapshot_service(
    user_id, folder_id, project_id, snapshot_name=None
):
    if snapshot_name is not None:
        snapshot_name, _ = validate_name(snapshot_name, max_length=150)

    snapshot_id = new_snapshot_id()
    manifest = None

    # Pin each current file to an immutable tblProjectVersions record while
    # the owned project/file rows are locked in the normal DB transaction.
    with student_transaction(user_id) as (cursor, student_id):
        project = _check_active_project(cursor, student_id, folder_id, project_id)
        file_rows = files_repo.list_active_project_files_for_snapshot_repo(
            cursor, student_id, folder_id, project_id
        )
        snapshot_files = []

        for file_row in file_rows:
            if file_row["folder_id"] is not None:
                try:
                    folders_repo.get_active_folder_repo(
                        cursor, student_id, file_row["folder_id"]
                    )
                except FolderError as exc:
                    raise FolderError(
                        f"File {file_row['file_name']} references a folder that is not active.",
                        409,
                    ) from exc
            current_path = _storage_path(file_row["current_path"])
            if not current_path.is_file():
                raise FolderError(
                    f"File contents are missing for {file_row['file_name']}.", 409
                )
            actual_size = current_path.stat().st_size
            if int(file_row["file_size"]) != actual_size:
                raise FolderError(
                    f"Stored size differs from file metadata for {file_row['file_name']}.",
                    409,
                )
            version = versions_repo.get_version_by_path_repo(
                cursor, file_row["id"], str(current_path)
            )
            if version is None:
                latest = versions_repo.latest_version_number_repo(
                    cursor, file_row["id"]
                )
                inserted_version = versions_repo.insert_version_repo(
                    cursor, file_row["id"], latest + 1,
                    str(current_path), actual_size, user_id,
                )
                if inserted_version is not None:
                    # The repository's normal insert helper returns VERSION_COLUMNS,
                    # which intentionally omits file_path. Re-read through the
                    # lifecycle helper whose projection includes that field.
                    version = versions_repo.get_version_by_id_repo(
                        cursor, file_row["id"], inserted_version["id"]
                    )
            if version is None:
                raise FolderError(
                    f"Could not record the current version for {file_row['file_name']}.",
                    500,
                )
            if Path(version["file_path"]).resolve() != current_path:
                raise FolderError("Current file/version paths are inconsistent.", 409)
            if int(version["file_size"]) != actual_size:
                raise FolderError(
                    f"Stored size differs from the version record for {file_row['file_name']}. ",
                    409,
                )

            snapshot_files.append({
                "project_file_id": int(file_row["id"]),
                "version_id": int(version["id"]),
                "version_number": int(version["version_number"]),
                "file_name": file_row["file_name"],
                "file_type": file_row["file_type"],
                "file_size": int(actual_size),
                "folder_id": (
                    int(file_row["folder_id"])
                    if file_row["folder_id"] is not None else None
                ),
                "sha256": _sha256_file(current_path),
            })

        manifest = {
            "schema_version": 1,
            "snapshot_id": snapshot_id,
            "student_id": int(student_id),
            "project_id": int(project_id),
            "project_folder_id": int(project["folder_id"]),
            "project_name": project["project_name"],
            "description": project["description"],
            "snapshot_name": snapshot_name,
            "created_by": int(user_id),
            "created_at": _iso_utc_now(),
            "file_count": len(snapshot_files),
            "files": snapshot_files,
        }

    # Save only after the DB transaction commits, so a manifest never points
    # to version rows that were rolled back. Failed writes may leave valid
    # version history rows, but do not create a visible snapshot manifest.
    try:
        write_snapshot_manifest(student_id, project_id, manifest)
    except Exception as exc:
        current_app.logger.exception("Could not write project snapshot JSON manifest")
        raise FolderError(
            "Snapshot could not be saved. No snapshot manifest was created.", 500
        ) from exc

    return _snapshot_data(manifest)


def list_project_snapshots_service(
    user_id, folder_id, project_id, limit=50, offset=0
):
    with student_transaction(user_id) as (cursor, student_id):
        _check_active_project(cursor, student_id, folder_id, project_id)
        manifests = list_snapshot_manifests(student_id, project_id)

    manifests.sort(
        key=lambda item: (item.get("created_at", ""), item.get("snapshot_id", "")),
        reverse=True,
    )
    page = manifests[offset:offset + limit]
    return {
        "snapshots": [_snapshot_data(item) for item in page],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(manifests) > offset + limit,
        },
    }


def restore_project_snapshot_service(
    user_id, folder_id, project_id, snapshot_id
):
    saved_paths = []
    try:
        with student_transaction(user_id) as (cursor, student_id):
            project = _check_active_project(cursor, student_id, folder_id, project_id)
            try:
                safe_snapshot_id = normalize_snapshot_id(snapshot_id)
                manifest = read_snapshot_manifest(
                    student_id, project_id, safe_snapshot_id
                )
            except SnapshotManifestError as exc:
                message = str(exc)
                if "not found" in message.lower():
                    status_code = 404
                elif "invalid snapshot id" in message.lower():
                    status_code = 400
                else:
                    status_code = 409
                raise FolderError(message, status_code) from exc

            if manifest["project_folder_id"] != folder_id:
                raise FolderError(
                    "Snapshot belongs to a different project folder.", 409
                )
            snapshot_project_name = _validated_manifest_name(
                manifest["project_name"], "project name", 150
            )
            description = manifest["description"]
            if description is not None:
                if not isinstance(description, str):
                    raise FolderError("Snapshot contains an invalid project description.", 409)
                try:
                    description_size = len(description.encode("utf-8"))
                except UnicodeEncodeError as exc:
                    raise FolderError(
                        "Snapshot contains an invalid project description.", 409
                    ) from exc
                if description_size > 65535:
                    raise FolderError(
                        "Snapshot project description is too long.", 409
                    )
            if projects_repo.active_project_name_exists_excluding_repo(
                cursor, student_id, folder_id, snapshot_project_name, project_id
            ):
                raise FolderError(
                    "Another active project already uses the snapshot project name. "
                    "Rename that project before recovery.", 409,
                )

            # Verify all referenced file rows, folder assignments, versions,
            # storage paths, sizes, checksums, and names before changing rows.
            prepared = []
            target_ids = set()
            seen_names = set()
            for item in manifest["files"]:
                file_id = item["project_file_id"]
                target_ids.add(file_id)
                _validated_manifest_name(item["file_name"], "file name", 255)

                # The file APIs treat names as project-wide identifiers; reject a
                # tampered/legacy manifest that would restore ambiguous names.
                normalized_name = item["file_name"].casefold()
                if normalized_name in seen_names:
                    raise FolderError(
                        "Snapshot contains duplicate file names; recovery was not applied.",
                        409,
                    )
                seen_names.add(normalized_name)
                if item["folder_id"] is not None:
                    try:
                        folders_repo.get_active_folder_repo(
                            cursor, student_id, item["folder_id"]
                        )
                    except FolderError as exc:
                        raise FolderError(
                            "A folder referenced by the snapshot is no longer active. "
                            "Restore that folder first.", 409,
                        ) from exc

                file_row = files_repo.get_project_file_record_for_snapshot_repo(
                    cursor, student_id, folder_id, project_id, file_id
                )
                if file_row is None:
                    raise FolderError(
                        "A file record referenced by the snapshot no longer exists.", 409
                    )
                version = versions_repo.get_version_by_id_repo(
                    cursor, file_id, item["version_id"]
                )
                if version is None or int(version["version_number"]) != item["version_number"]:
                    raise FolderError(
                        "A historical version referenced by the snapshot no longer exists.",
                        409,
                    )
                source_path = _storage_path(version["file_path"])
                if not source_path.is_file():
                    raise FolderError(
                        f"Snapshot contents are missing for {item['file_name']}.", 409
                    )
                actual_size = source_path.stat().st_size
                if actual_size != item["file_size"] or actual_size != int(version["file_size"]):
                    raise FolderError(
                        f"Snapshot size validation failed for {item['file_name']}.", 409
                    )
                if _sha256_file(source_path) != item["sha256"]:
                    raise FolderError(
                        f"Snapshot checksum validation failed for {item['file_name']}.", 409
                    )
                prepared.append((item, source_path))

            # Soft-delete files added after the snapshot. Do not physically
            # remove their contents or version history.
            active_files = files_repo.list_active_project_files_for_snapshot_repo(
                cursor, student_id, folder_id, project_id
            )
            cursor.execute("SELECT UTC_TIMESTAMP() AS deleted_at")
            deletion_time = cursor.fetchone()["deleted_at"]
            for current_file in active_files:
                if current_file["id"] not in target_ids:
                    files_repo.soft_delete_project_file_repo(
                        cursor, project_id, current_file["id"], deletion_time
                    )

            restored_count = 0
            for item, source_path in prepared:
                destination_dir = (
                    Path(current_app.instance_path) / "project_uploads"
                    / str(student_id) / str(project_id)
                )
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / uuid4().hex
                if len(str(destination)) > 500:
                    raise FolderError("Restored storage path is too long.", 500)
                saved_paths.append(destination)
                shutil.copyfile(source_path, destination)
                file_size = destination.stat().st_size
                if (file_size != item["file_size"]
                        or _sha256_file(destination) != item["sha256"]):
                    raise FolderError(
                        f"Snapshot content changed while restoring {item['file_name']}.",
                        409,
                    )

                latest = versions_repo.latest_version_number_repo(
                    cursor, item["project_file_id"]
                )
                new_version = versions_repo.insert_version_repo(
                    cursor, item["project_file_id"], latest + 1,
                    str(destination), file_size, user_id,
                )
                if new_version is None:
                    raise FolderError("Restored version could not be recorded.", 500)

                updated = files_repo.restore_snapshot_file_repo(
                    cursor, project_id, item["project_file_id"],
                    item["folder_id"], item["file_name"], item["file_type"],
                    file_size, str(destination),
                )
                if updated is None:
                    raise FolderError(
                        "Restored file could not be retrieved from the database.", 500
                    )
                restored_count += 1

            updated_project = projects_repo.update_project_repo(
                cursor, student_id, folder_id, project_id,
                snapshot_project_name, description, True,
            )
            if updated_project is None:
                raise FolderError("Project metadata could not be restored.", 500)

            return {
                "project_id": project_id,
                "snapshot_id": safe_snapshot_id,
                "restored_file_count": restored_count,
                "project_name": snapshot_project_name,
                "message": (
                    "Project metadata and file set restored from the selected snapshot. "
                    "Restored files were recorded as new current versions."
                ),
            }
    except Exception:
        # DB rolls back through student_transaction; remove only storage copies
        # created by this request, never existing historical version files.
        for path in saved_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Could not clean up a failed project snapshot restore"
                )
        raise