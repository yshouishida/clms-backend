import hashlib
import os
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from flask import current_app

from backend.repositories import captures_repository as repo
from backend.repositories import inventory_repository as inventory
from backend.repositories import monitoring_repository
from backend.services.monitoring_service import agent_workstation, observed_time
from backend.services.rfid_service import positive_id
from backend.utils.domain_error import DomainError
from backend.utils.snapshot_image import validate_png


def snapshot_root():
    root = Path(current_app.config.get(
        "SNAPSHOT_STORAGE_ROOT", Path(current_app.instance_path) / "camera_captures",
    )).resolve()
    static = Path(current_app.static_folder).resolve() if current_app.static_folder else None
    if static and (root == static or static in root.parents):
        raise DomainError("Snapshot storage configuration is invalid.", 503)
    return root


def stored_snapshot(filename):
    if not isinstance(filename, str) or not re.fullmatch(r"[0-9a-f]{32}\.png", filename):
        raise DomainError("Snapshot file is unavailable.", 404)
    root = snapshot_root()
    path = (root / filename).resolve()
    if path.parent != root or not path.is_file():
        raise DomainError("Snapshot file is unavailable.", 404)
    return path


def capture_fields(body):
    if not isinstance(body, dict) or set(body) != {"session_id", "camera_id", "captured_at"}:
        raise DomainError("Send session_id, camera_id, and captured_at.")
    positive_id(body["session_id"], "session_id")
    positive_id(body["camera_id"], "camera_id")
    return observed_time(body["captured_at"])


def check_capture_time(session, timestamp):
    login_utc = session["login_at"] - timedelta(seconds=session["utc_offset"])
    if timestamp < login_utc:
        raise DomainError("Capture timestamp precedes the session login.")


def upload_capture_service(workstation_id, fields, uploaded):
    timestamp = capture_fields(fields)
    if uploaded is None:
        raise DomainError("An image file is required.")
    limit = current_app.config["SNAPSHOT_MAX_BYTES"]
    data = uploaded.stream.read(limit + 1)
    if len(data) > limit:
        raise DomainError("Snapshot exceeds the configured size limit.", 413)
    data = validate_png(data, current_app.config["SNAPSHOT_MAX_PIXELS"])
    root = snapshot_root()
    filename = uuid4().hex + ".png"
    path = root / filename
    created = False
    try:
        with inventory.inventory_transaction() as cursor:
            agent_workstation(cursor, workstation_id)
            session, camera = repo.capture_session_repo(
                cursor, workstation_id, fields["session_id"], fields["camera_id"],
            )
            check_capture_time(session, timestamp)
            if camera["status"] != "Active" or camera["connection_status"] != "Connected":
                raise DomainError("Camera is not available; report the capture failure.", 409)
            existing = repo.existing_capture_repo(cursor, fields["session_id"], fields["camera_id"], "Captured")
            if existing:
                previous = stored_snapshot(existing["file_path"])
                if hashlib.sha256(previous.read_bytes()).digest() != hashlib.sha256(data).digest():
                    raise DomainError("A different login snapshot already exists.", 409)
                return {"capture_id": existing["id"], "capture_status": "Captured", "duplicate": True}, 200
            root.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as destination:
                created = True
                destination.write(data)
                destination.flush()
                os.fsync(destination.fileno())
            capture_id = repo.insert_capture_repo(
                cursor, fields["session_id"], fields["camera_id"], filename, timestamp, "Captured",
            )
        return {"capture_id": capture_id, "capture_status": "Captured", "duplicate": False}, 201
    except Exception:
        if created:
            try:
                # A lost commit acknowledgement must not delete a committed image.
                with inventory.inventory_transaction() as cursor:
                    committed = repo.stored_capture_exists_repo(cursor, filename)
                if not committed:
                    path.unlink(missing_ok=True)
            except Exception:
                current_app.logger.error("Snapshot cleanup requires storage reconciliation")
        raise


def capture_failure_service(workstation_id, body):
    if not isinstance(body, dict) or set(body) != {"session_id", "camera_id", "captured_at", "reason"}:
        raise DomainError("Send session_id, camera_id, captured_at, and reason.")
    fields = {key: body[key] for key in ("session_id", "camera_id", "captured_at")}
    timestamp = capture_fields(fields)
    if body["reason"] not in ("Disconnected", "Unavailable", "Capture error", "Upload error"):
        raise DomainError("Invalid capture failure reason.")
    with inventory.inventory_transaction() as cursor:
        agent_workstation(cursor, workstation_id)
        session, camera = repo.capture_session_repo(cursor, workstation_id, body["session_id"], body["camera_id"])
        check_capture_time(session, timestamp)
        existing = repo.existing_capture_repo(cursor, body["session_id"], body["camera_id"], "Failed")
        if existing:
            return {"capture_id": existing["id"], "capture_status": "Failed", "duplicate": True}, 200
        # V04 requires a path even for Failed attempts; empty means no stored file.
        capture_id = repo.insert_capture_repo(cursor, body["session_id"], body["camera_id"], "", timestamp, "Failed")
        latest = monitoring_repository.latest_agent_status_repo(cursor, workstation_id)
        if body["reason"] == "Disconnected" and (latest is None or latest["recorded_at"] <= timestamp):
            inventory.save_inventory_repo(cursor, "cameras", {"connection_status": "Disconnected"}, camera["id"])
        inventory.system_log_repo(cursor, workstation_id, "Warning", "CameraCapture",
                                  f"Capture {capture_id}: {body['reason']}")
        return {"capture_id": capture_id, "capture_status": "Failed", "duplicate": False}, 201


def get_capture_service(capture_id, user_id, role, download=False):
    with inventory.inventory_transaction() as cursor:
        row = repo.capture_metadata_repo(cursor, capture_id, user_id, role)
    if download:
        if row["capture_status"] != "Captured":
            raise DomainError("This capture has no snapshot file.", 404)
        return stored_snapshot(row["file_path"])
    row.pop("file_path")
    row.pop("user_id")
    return row
