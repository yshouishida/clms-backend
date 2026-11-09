from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import uuid4

from flask import current_app


_SNAPSHOT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_SCHEMA_VERSION = 1


class SnapshotManifestError(ValueError):
    """A saved snapshot manifest is missing, invalid, or inconsistent."""


def new_snapshot_id() -> str:
    """Return a filesystem-safe UUID identifier for a snapshot manifest."""
    return uuid4().hex


def normalize_snapshot_id(snapshot_id: str) -> str:
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise SnapshotManifestError("Invalid snapshot ID.")
    return snapshot_id


def _snapshot_directory(student_id: int, project_id: int) -> Path:
    if type(student_id) is not int or student_id < 1:
        raise SnapshotManifestError("Invalid student ID.")

    if type(project_id) is not int or project_id < 1:
        raise SnapshotManifestError("Invalid project ID.")

    instance_root = Path(current_app.instance_path).resolve()
    snapshots_root = (instance_root / "project_snapshots").resolve()
    directory = (snapshots_root / str(student_id) / str(project_id)).resolve()

    if not directory.is_relative_to(snapshots_root):
        raise SnapshotManifestError("Snapshot directory is outside the configured storage root.")
    return directory


def _manifest_path(student_id: int, project_id: int, snapshot_id: str) -> Path:
    safe_id = normalize_snapshot_id(snapshot_id)
    directory = _snapshot_directory(student_id, project_id)
    path = (directory / f"{safe_id}.json").resolve()
    if not path.is_relative_to(directory):
        raise SnapshotManifestError("Snapshot manifest path is invalid.")
    return path


def _validate_manifest(manifest, student_id, project_id, expected_snapshot_id=None):
    if not isinstance(manifest, dict):
        raise SnapshotManifestError("Snapshot manifest must be a JSON object.")

    sid = manifest.get("snapshot_id")
    try:
        sid = normalize_snapshot_id(sid)
    except SnapshotManifestError as exc:
        raise SnapshotManifestError("Snapshot manifest contains an invalid ID.") from exc

    if expected_snapshot_id is not None and sid != expected_snapshot_id:
        raise SnapshotManifestError("Snapshot ID does not match its manifest filename.")

    if manifest.get("schema_version") != _MANIFEST_SCHEMA_VERSION:
        raise SnapshotManifestError("Unsupported snapshot manifest version.")

    if type(manifest.get("student_id")) is not int or manifest["student_id"] != student_id:
        raise SnapshotManifestError("Snapshot belongs to a different student.")

    if type(manifest.get("project_id")) is not int or manifest["project_id"] != project_id:
        raise SnapshotManifestError("Snapshot belongs to a different project.")

    if type(manifest.get("project_folder_id")) is not int or manifest["project_folder_id"] < 1:
        raise SnapshotManifestError("Snapshot manifest has an invalid project folder ID.")

    if type(manifest.get("created_by")) is not int or manifest["created_by"] < 1:
        raise SnapshotManifestError("Snapshot manifest has an invalid creator ID.")

    if not isinstance(manifest.get("created_at"), str) or not manifest["created_at"]:
        raise SnapshotManifestError("Snapshot manifest has no creation timestamp.")

    if not isinstance(manifest.get("project_name"), str) or not manifest["project_name"].strip():
        raise SnapshotManifestError("Snapshot manifest has an invalid project name.")

    if len(manifest["project_name"]) > 150:
        raise SnapshotManifestError("Snapshot project name is too long.")

    if manifest.get("description") is not None and not isinstance(manifest.get("description"), str):
        raise SnapshotManifestError("Snapshot description must be text or null.")
    snapshot_name = manifest.get("snapshot_name")

    if snapshot_name is not None and (not isinstance(snapshot_name, str) or len(snapshot_name) > 150):
        raise SnapshotManifestError("Snapshot name must be at most 150 characters.")

    files = manifest.get("files")
    if not isinstance(files, list):
        raise SnapshotManifestError("Snapshot manifest has no file list.")
    seen_file_ids = set()

    for item in files:
        if not isinstance(item, dict):
            raise SnapshotManifestError("Snapshot manifest contains an invalid file entry.")

        for field in ("project_file_id", "version_id", "version_number"):
            if type(item.get(field)) is not int or item[field] < 1:
                raise SnapshotManifestError(f"Snapshot file entry has an invalid {field}.")

        file_id = item["project_file_id"]
        if file_id in seen_file_ids:
            raise SnapshotManifestError("Snapshot manifest contains a duplicate file ID.")

        seen_file_ids.add(file_id)
        if not isinstance(item.get("file_name"), str) or not item["file_name"] or len(item["file_name"]) > 255:
            raise SnapshotManifestError("Snapshot manifest contains an invalid filename.")

        file_type = item.get("file_type")
        if file_type is not None and (not isinstance(file_type, str) or len(file_type) > 100):
            raise SnapshotManifestError("Snapshot manifest contains an invalid file type.")

        if type(item.get("file_size")) is not int or item["file_size"] < 0:
            raise SnapshotManifestError("Snapshot manifest contains an invalid file size.")

        folder_id = item.get("folder_id")
        if folder_id is not None and (type(folder_id) is not int or folder_id < 1):
            raise SnapshotManifestError("Snapshot manifest contains an invalid file folder ID.")

        digest = item.get("sha256")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise SnapshotManifestError("Snapshot manifest contains an invalid file checksum.")

    if manifest.get("file_count") != len(files):
        raise SnapshotManifestError("Snapshot file count does not match its manifest.")
    return manifest


def write_snapshot_manifest(student_id: int, project_id: int, manifest: dict) -> Path:
    """Atomically save a validated manifest without creating or altering DB tables."""
    snapshot_id = normalize_snapshot_id(manifest.get("snapshot_id"))
    checked = _validate_manifest(manifest, student_id, project_id, snapshot_id)
    directory = _snapshot_directory(student_id, project_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = _manifest_path(student_id, project_id, snapshot_id)
    if target.exists():
        raise SnapshotManifestError("Snapshot ID already exists; retry creation.")

    temporary = directory / f".{snapshot_id}.{uuid4().hex}.tmp"
    fd = None
    try:
        # Restrictive creation mode on platforms that support POSIX permissions.
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = None
            json.dump(checked, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return target
    except Exception:
        if fd is not None:
            os.close(fd)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Could not clean up temporary snapshot manifest")
        raise


def read_snapshot_manifest(student_id: int, project_id: int, snapshot_id: str) -> dict:
    safe_id = normalize_snapshot_id(snapshot_id)
    path = _manifest_path(student_id, project_id, safe_id)
    try:
        with path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except FileNotFoundError as exc:
        raise SnapshotManifestError("Project snapshot was not found.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotManifestError("Project snapshot manifest cannot be read.") from exc
    return _validate_manifest(manifest, student_id, project_id, safe_id)


def list_snapshot_manifests(student_id: int, project_id: int) -> list[dict]:
    directory = _snapshot_directory(student_id, project_id)
    if not directory.exists():
        return []

    manifests = []
    for path in directory.glob("*.json"):
        try:
            manifests.append(read_snapshot_manifest(student_id, project_id, path.stem))
        except SnapshotManifestError:
            # One corrupt manifest should not make every other snapshot invisible.
            current_app.logger.warning(
                "Skipping invalid project snapshot manifest %s", path.name,
                exc_info=True,
            )
    return manifests