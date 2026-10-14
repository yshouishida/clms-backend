import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import current_app

from backend.repositories import inventory_repository as inventory
from backend.repositories import monitoring_repository as repo
from backend.services.rfid_service import positive_id
from backend.utils.agent_auth import heartbeat_policy
from backend.utils.domain_error import DomainError


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def observed_time(value):
    if not isinstance(value, str):
        raise DomainError("observed_at must be an ISO-8601 timestamp with a timezone.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
    except (ValueError, OverflowError):
        raise DomainError("observed_at must be a valid timestamp with a timezone.")
    _, timeout, skew = heartbeat_policy()
    age = (utc_now() - parsed).total_seconds()
    if age < -skew or age > timeout:
        raise DomainError("Timestamp is outside the configured reporting window.")
    return parsed


def metric(value, name):
    if type(value) not in (int, float):
        raise DomainError(f"{name} must be a number between 0 and 100.")
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not 0 <= result <= 100:
            raise InvalidOperation()
        return result.quantize(Decimal("0.01"))
    except InvalidOperation:
        raise DomainError(f"{name} must be a number between 0 and 100.")


def agent_workstation(cursor, workstation_id):
    inventory.lock_workstations_repo(cursor, [workstation_id])
    workstation = inventory.get_inventory_repo(cursor, "workstations", workstation_id)
    if workstation["status"] == "Retired":
        raise DomainError("Workstation is retired.", 403)
    return workstation


def agent_configuration_service(workstation_id):
    interval, timeout, skew = heartbeat_policy()
    with inventory.inventory_transaction() as cursor:
        workstation = agent_workstation(cursor, workstation_id)
        devices = repo.assigned_devices_repo(cursor, workstation_id)
    return {
        "workstation_id": workstation_id,
        "pc_name": workstation["pc_name"],
        "laboratory_id": workstation["laboratory_id"],
        "devices": devices,
        "heartbeat_interval_seconds": interval,
        "offline_after_seconds": timeout,
        "max_clock_skew_seconds": skew,
        "snapshot_max_bytes": current_app.config["SNAPSHOT_MAX_BYTES"],
        "snapshot_max_pixels": current_app.config["SNAPSHOT_MAX_PIXELS"],
        "snapshot_format": "PNG (8-bit RGB/RGBA, non-interlaced)",
    }


def heartbeat_service(workstation_id, body):
    required = {"observed_at", "cpu_usage", "ram_usage", "storage_usage", "network_status", "devices"}
    if (
        not isinstance(body, dict) or required - set(body)
        or set(body) - required - {"session_id", "online_status"}
    ):
        raise DomainError("Send the documented heartbeat fields.")
    data = {name: metric(body[name], name) for name in ("cpu_usage", "ram_usage", "storage_usage")}
    data["recorded_at"] = observed_time(body["observed_at"])
    data["online_status"] = body.get("online_status", "Online")
    data["network_status"] = body["network_status"]
    data["session_id"] = body.get("session_id")
    if (
        data["online_status"] not in ("Online", "Offline")
        or data["network_status"] not in ("Connected", "Disconnected")
    ):
        raise DomainError("Invalid connectivity status.")
    if data["session_id"] is not None:
        positive_id(data["session_id"], "session_id")
    devices = body["devices"]
    if not isinstance(devices, list) or len(devices) > 20:
        raise DomainError("devices must be a list of assigned hardware (maximum 20).")
    reported = {}
    for device in devices:
        if not isinstance(device, dict) or set(device) != {"kind", "id", "connection_status"}:
            raise DomainError("Each device requires kind, id, and connection_status.")
        if (
            device["kind"] not in inventory.DEVICE_KINDS
            or device["connection_status"] not in ("Connected", "Disconnected")
        ):
            raise DomainError("Invalid hardware type or connection status.")
        positive_id(device["id"], "device id")
        key = (device["kind"], device["id"])
        if key in reported:
            raise DomainError("Duplicate hardware report.")
        reported[key] = device["connection_status"]

    with inventory.inventory_transaction() as cursor:
        agent_workstation(cursor, workstation_id)
        if (
            data["session_id"] is not None
            and data["session_id"] not in repo.active_sessions_repo(cursor, workstation_id)
        ):
            raise DomainError("Session is not active on this workstation.", 409)
        assigned = repo.assigned_devices_repo(cursor, workstation_id)
        if set(reported) != {(device["kind"], device["id"]) for device in assigned}:
            raise DomainError("Report exactly the active devices assigned to this workstation.", 409)
        for kind, field in (("cameras", "camera_status"), ("rfid-readers", "rfid_status")):
            states = [state for (reported_kind, _), state in reported.items() if reported_kind == kind]
            data[field] = (
                "Not Available" if not states
                else "Connected" if all(state == "Connected" for state in states)
                else "Disconnected"
            )

        latest = repo.latest_agent_status_repo(cursor, workstation_id)
        if latest and data["recorded_at"] <= latest["recorded_at"]:
            if (
                all(latest[name] == value for name, value in data.items())
                and all(device["connection_status"] == reported[(device["kind"], device["id"])]
                        for device in assigned)
            ):
                return {"pc_status_id": latest["id"], "duplicate": True}, 200
            raise DomainError("Heartbeat is older than or conflicts with the latest report.", 409)

        status_id = repo.insert_heartbeat_repo(cursor, workstation_id, data)
        for device in assigned:
            state = reported[(device["kind"], device["id"])]
            if device["connection_status"] != state:
                inventory.save_inventory_repo(cursor, device["kind"], {"connection_status": state}, device["id"])
                inventory.system_log_repo(
                    cursor, workstation_id, "Info", "HardwareAvailability",
                    json.dumps({"pc_status_id": status_id, **device, "connection_status": state}),
                )
        if latest is None or latest["online_status"] != data["online_status"]:
            inventory.system_log_repo(cursor, workstation_id, "Info", "AgentConnectivity", data["online_status"])
        return {"pc_status_id": status_id, "duplicate": False}, 201


def dashboard_service(laboratory_id=None, include_students=False):
    interval, timeout, _ = heartbeat_policy()
    now = utc_now()
    with inventory.inventory_transaction() as cursor:
        rows = repo.dashboard_rows_repo(cursor, laboratory_id)
        students = repo.active_student_details_repo(cursor) if include_students else {}
    counts = {name: 0 for name in (
        "total", "online", "offline", "in_use", "available",
        "with_rfid", "with_camera", "with_arduino", "hardware_unavailable",
    )}
    for row in rows:
        if include_students:
            row["current_student"] = students.get(row["session_id"]) if row["active_session_count"] == 1 else None
        last = row["last_heartbeat_at"]
        fresh = last is not None and (now - last).total_seconds() < timeout
        row["online"] = fresh and row["reported_online_status"] == "Online"
        row["connectivity_reason"] = (
            "Never reported" if last is None
            else "Stale" if not fresh
            else row["reported_online_status"]
        )
        row["in_use"] = row["active_session_count"] > 0
        row["available"] = (
            row["online"] and not row["in_use"] and row["status"] == "Active"
            and row["condition"] == "Working" and row["laboratory_status"] == "Active"
        )
        row["hardware_unavailable"] = bool(
            row["unavailable_readers"] + row["unavailable_cameras"] + row["unavailable_arduinos"]
            or (not row["online"] and row["reader_count"] + row["camera_count"] + row["arduino_count"])
        )
        counts["total"] += 1
        counts["online"] += int(row["online"])
        counts["offline"] += int(not row["online"])
        for field in ("in_use", "available", "hardware_unavailable"):
            counts[field] += int(row[field])
        for label, column in (
            ("with_rfid", "reader_count"), ("with_camera", "camera_count"),
            ("with_arduino", "arduino_count"),
        ):
            counts[label] += int(row[column] > 0)
    return {"counts": counts, "workstations": rows, "as_of": now,
            "heartbeat_interval_seconds": interval, "offline_after_seconds": timeout}


def agent_error_service(workstation_id, body):
    if not isinstance(body, dict) or set(body) != {"level", "component", "message"}:
        raise DomainError("Send level, component, and message.")
    if body["level"] not in ("Info", "Warning", "Error", "Critical"):
        raise DomainError("Invalid log level.")
    if body["component"] not in ("Agent", "Network", "Camera", "RFID", "Arduino"):
        raise DomainError("Invalid component.")
    message = body["message"]
    if not isinstance(message, str) or not message.strip() or len(message.encode("utf-8", errors="replace")) > 2000:
        raise DomainError("message must contain 1 to 2000 UTF-8 bytes.")
    with inventory.inventory_transaction() as cursor:
        agent_workstation(cursor, workstation_id)
        cursor.execute(
            """
            SELECT
                id
            FROM tblSystemLogs
            WHERE workstation_id = %s AND source = %s AND log_level = %s
                AND message = %s AND created_at >= UTC_TIMESTAMP() - INTERVAL 60 SECOND
            ORDER BY id DESC
            LIMIT 1
            """,
            (workstation_id, "Agent:" + body["component"], body["level"], message.strip()),
        )
        existing = cursor.fetchone()
        if existing:
            return {"system_log_id": existing["id"], "duplicate": True}
        log_id = inventory.system_log_repo(cursor, workstation_id, body["level"],
                                          "Agent:" + body["component"], message.strip())
        return {"system_log_id": log_id, "duplicate": False}
