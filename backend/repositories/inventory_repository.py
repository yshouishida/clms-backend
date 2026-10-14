import json
from contextlib import contextmanager

from backend.database.connection import get_connection
from backend.utils.domain_error import DomainError


INVENTORY = {
    "laboratories": ("tblLaboratories", (
        "laboratory_name", "room_number", "description", "status",
    )),
    "workstations": ("tblWorkstations", (
        "laboratory_id", "pc_name", "asset_tag", "ip_address", "processor",
        "ram", "storage", "operating_system", "status", "condition",
    )),
    "rfid-readers": ("tblRFIDReaders", (
        "workstation_id", "device_name", "serial_number", "connection_status", "status",
    )),
    "arduinos": ("tblArduinoDevices", (
        "workstation_id", "device_name", "serial_port", "connection_status", "status",
    )),
    "cameras": ("tblCameras", (
        "workstation_id", "device_name", "connection_status", "status",
    )),
}
DEVICE_KINDS = ("rfid-readers", "arduinos", "cameras")


@contextmanager
def inventory_transaction():
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_inventory_repo(cursor, kind, record_id, lock=False):
    table, columns = INVENTORY[kind]
    selected = ",\n            ".join("`" + name + "`" for name in ("id",) + columns)
    query = f"""
        SELECT
            {selected}
        FROM {table}
        WHERE id = %s
    """
    if lock:
        query += " FOR UPDATE"
    cursor.execute(query, (record_id,))
    return cursor.fetchone()


def list_inventory_repo(cursor, kind, limit, offset, parent_id=None):
    table, columns = INVENTORY[kind]
    selected = ",\n            ".join("`" + name + "`" for name in ("id",) + columns)
    query = f"""
        SELECT
            {selected}
        FROM {table}
    """
    params = []
    if parent_id is not None:
        parent = "laboratory_id" if kind == "workstations" else "workstation_id"
        query += f" WHERE {parent} = %s"
        params.append(parent_id)
    query += " ORDER BY id LIMIT %s OFFSET %s"
    cursor.execute(query, params + [limit, offset])
    return cursor.fetchall()


def save_inventory_repo(cursor, kind, fields, record_id=None):
    table, allowed = INVENTORY[kind]
    if not fields or set(fields) - set(allowed):
        raise ValueError("Invalid inventory fields")
    columns = list(fields)
    if record_id is None:
        names = ", ".join("`" + column + "`" for column in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        cursor.execute(
            f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        return cursor.lastrowid

    assignments = ",\n            ".join("`" + column + "` = %s" for column in columns)
    cursor.execute(
        f"""
        UPDATE {table}
        SET {assignments}
        WHERE id = %s
        """,
        tuple(fields.values()) + (record_id,),
    )
    return record_id


def lock_workstations_repo(cursor, workstation_ids):
    for workstation_id in sorted(set(workstation_ids)):
        if not get_inventory_repo(cursor, "workstations", workstation_id, True):
            raise DomainError("Workstation not found.", 404)


def require_idle_repo(cursor, workstation_id):
    cursor.execute(
        """
        SELECT
            id
        FROM tblLaboratorySessions
        WHERE workstation_id = %s AND status = 'Active'
        LIMIT 1
        FOR UPDATE
        """,
        (workstation_id,),
    )
    if cursor.fetchone():
        raise DomainError("Workstation has an active laboratory session.", 409)


def check_device_assignment_repo(cursor, kind, workstation_id, record_id):
    table = INVENTORY[kind][0]
    cursor.execute(
        f"""
        SELECT
            id
        FROM {table}
        WHERE workstation_id = %s AND status = 'Active' AND id <> %s
        LIMIT 1
        FOR UPDATE
        """,
        (workstation_id, record_id or 0),
    )
    if cursor.fetchone():
        raise DomainError("An active device of this type is already assigned.", 409)


def system_log_repo(cursor, workstation_id, level, source, message):
    cursor.execute(
        """
        INSERT INTO tblSystemLogs
            (workstation_id, log_level, source, message, created_at)
        VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())
        """,
        (workstation_id, level, source, message),
    )
    return cursor.lastrowid


def inventory_event_repo(cursor, kind, before, after, user_id):
    system_log_repo(
        cursor, after.get("workstation_id", after["id"] if kind == "workstations" else None),
        "Info", "Inventory",
        json.dumps({"kind": kind, "user_id": user_id, "before": before, "after": after}),
    )
