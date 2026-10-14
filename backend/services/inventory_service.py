import ipaddress

from flask import current_app

from backend.repositories import inventory_repository as repo
from backend.services.rfid_service import positive_id
from backend.utils.domain_error import DomainError


TEXT_LIMITS = {
    "laboratory_name": 100, "room_number": 30, "description": 4000,
    "pc_name": 100, "asset_tag": 50, "ip_address": 45, "processor": 150,
    "ram": 50, "storage": 100, "operating_system": 100,
    "device_name": 100, "serial_number": 100, "serial_port": 30,
}


def registration_devices():
    devices = current_app.config.get("REGISTRATION_DEVICE_IDS", {})
    if (
        not isinstance(devices, dict) or set(devices) - {"rfid-readers", "arduinos"}
        or any(type(value) is not int or value < 1 for value in devices.values())
    ):
        raise DomainError("Registration device configuration is invalid.", 503)
    return devices


def inventory_fields(kind, body, creating):
    if kind not in repo.INVENTORY:
        raise DomainError("Inventory type not found.", 404)
    if not isinstance(body, dict) or not body or set(body) - set(repo.INVENTORY[kind][1]):
        raise DomainError("Send supported inventory fields in a JSON object.")
    fields = dict(body)
    required = {
        "laboratories": {"laboratory_name", "room_number"},
        "workstations": {"laboratory_id", "pc_name", "asset_tag"},
        "rfid-readers": {"device_name"},
        "arduinos": {"device_name"},
        "cameras": {"device_name", "workstation_id"},
    }[kind]
    if creating and required - set(fields):
        raise DomainError("Missing fields: " + ", ".join(sorted(required - set(fields))))
    for name, value in fields.items():
        if name in TEXT_LIMITS:
            if value is None and name not in required:
                continue
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > TEXT_LIMITS[name]:
                raise DomainError(f"{name} must contain 1 to {TEXT_LIMITS[name]} characters.")
            fields[name] = value.strip()
        elif name in ("laboratory_id", "workstation_id"):
            if value is None and kind in ("rfid-readers", "arduinos"):
                continue
            positive_id(value, name)
        else:
            options = {
                "connection_status": ("Connected", "Disconnected"),
                "condition": ("Working", "Defective", "For Inspection"),
                "status": (
                    ("Active", "Inactive") if kind == "laboratories"
                    else ("Active", "Under Maintenance", "Retired") if kind == "workstations"
                    else ("Active", "Inactive", "Defective")
                ),
            }
            if value not in options[name]:
                raise DomainError(f"Invalid {name}.")
    if fields.get("ip_address"):
        try:
            ipaddress.ip_address(fields["ip_address"])
        except ValueError:
            raise DomainError("ip_address must be an IPv4 or IPv6 address.")
    return fields


def inventory_data(kind, row):
    if kind in repo.DEVICE_KINDS:
        designated = registration_devices().get(kind) == row["id"]
        row["assignment"] = (
            "Workstation" if row["workstation_id"] is not None
            else "Registration Station" if designated else "Unassigned"
        )
    return row


def list_inventory_service(kind, limit, offset, parent_id=None):
    if kind not in repo.INVENTORY:
        raise DomainError("Inventory type not found.", 404)
    with repo.inventory_transaction() as cursor:
        if parent_id is not None:
            parent_kind = "laboratories" if kind == "workstations" else "workstations"
            if not repo.get_inventory_repo(cursor, parent_kind, parent_id):
                raise DomainError("Parent record not found.", 404)
        return [inventory_data(kind, row) for row in
                repo.list_inventory_repo(cursor, kind, limit, offset, parent_id)]


def get_inventory_service(kind, record_id):
    if kind not in repo.INVENTORY:
        raise DomainError("Inventory type not found.", 404)
    with repo.inventory_transaction() as cursor:
        row = repo.get_inventory_repo(cursor, kind, record_id)
        if row is None:
            raise DomainError("Inventory record not found.", 404)
        return inventory_data(kind, row)


def save_inventory_service(kind, body, user_id, record_id=None):
    fields = inventory_fields(kind, body, record_id is None)
    with repo.inventory_transaction() as cursor:
        before = repo.get_inventory_repo(cursor, kind, record_id) if record_id else None
        if record_id and before is None:
            raise DomainError("Inventory record not found.", 404)
        merged = {"status": "Active", "workstation_id": None, **(before or {}), **fields}

        if kind == "workstations":
            lab = repo.get_inventory_repo(cursor, "laboratories", merged["laboratory_id"], True)
            if not lab:
                raise DomainError("Laboratory not found.", 404)
            if lab["status"] != "Active" and merged["status"] == "Active":
                raise DomainError("Laboratory is inactive.", 409)
            if record_id:
                repo.lock_workstations_repo(cursor, [record_id])
                if repo.get_inventory_repo(cursor, kind, record_id, True) != before:
                    raise DomainError("Workstation changed; reload and retry.", 409)
                if any(name in fields and fields[name] != before[name]
                       for name in ("laboratory_id", "status", "condition")):
                    repo.require_idle_repo(cursor, record_id)

        elif kind == "laboratories" and record_id:
            repo.get_inventory_repo(cursor, kind, record_id, True)
            if fields.get("status") == "Inactive":
                cursor.execute(
                    """
                    SELECT
                        id
                    FROM tblWorkstations
                    WHERE laboratory_id = %s
                    ORDER BY id
                    FOR UPDATE
                    """,
                    (record_id,),
                )
                for row in cursor.fetchall():
                    repo.require_idle_repo(cursor, row["id"])

        elif kind in repo.DEVICE_KINDS:
            old_workstation = before["workstation_id"] if before else None
            new_workstation = merged["workstation_id"]
            repo.lock_workstations_repo(cursor, [value for value in
                                                (old_workstation, new_workstation) if value])
            if record_id:
                current = repo.get_inventory_repo(cursor, kind, record_id, True)
                if current != before:
                    raise DomainError("Device changed; reload and retry.", 409)
            if record_id and registration_devices().get(kind) == record_id and new_workstation is not None:
                raise DomainError("This device is designated for the registration station.", 409)
            if old_workstation != new_workstation:
                for value in set(filter(None, (old_workstation, new_workstation))):
                    repo.require_idle_repo(cursor, value)
                fields["connection_status"] = "Disconnected"
            if new_workstation is not None and merged["status"] == "Active":
                repo.check_device_assignment_repo(cursor, kind, new_workstation, record_id)

        record_id = repo.save_inventory_repo(cursor, kind, fields, record_id)
        after = repo.get_inventory_repo(cursor, kind, record_id)
        repo.inventory_event_repo(cursor, kind, before, after, user_id)
        return inventory_data(kind, after)
