from backend.repositories import inventory_repository as inventory
from backend.utils.domain_error import DomainError


PC_COLUMNS = """
    id,
    workstation_id,
    session_id,
    online_status,
    cpu_usage,
    ram_usage,
    storage_usage,
    network_status,
    camera_status,
    rfid_status,
    TIMESTAMPADD(
        SECOND, TIMESTAMPDIFF(SECOND, CURRENT_TIMESTAMP(), UTC_TIMESTAMP()), recorded_at
    ) AS recorded_at
"""


def latest_agent_status_repo(cursor, workstation_id):
    # Legacy student-session heartbeats leave network_status NULL.
    cursor.execute(
        f"""
        SELECT {PC_COLUMNS}
        FROM tblPCStatus
        WHERE workstation_id = %s AND network_status IS NOT NULL
        ORDER BY tblPCStatus.recorded_at DESC, id DESC
        LIMIT 1
        """,
        (workstation_id,),
    )
    return cursor.fetchone()


def active_sessions_repo(cursor, workstation_id):
    cursor.execute(
        """
        SELECT
            id
        FROM tblLaboratorySessions
        WHERE workstation_id = %s AND status = 'Active'
        ORDER BY id
        """,
        (workstation_id,),
    )
    return [row["id"] for row in cursor.fetchall()]


def assigned_devices_repo(cursor, workstation_id):
    result = []
    for kind in inventory.DEVICE_KINDS:
        table = inventory.INVENTORY[kind][0]
        cursor.execute(
            f"""
            SELECT
                id,
                connection_status
            FROM {table}
            WHERE workstation_id = %s AND status = 'Active'
            ORDER BY id
            """,
            (workstation_id,),
        )
        result.extend({"kind": kind, **row} for row in cursor.fetchall())
    return result


def insert_heartbeat_repo(cursor, workstation_id, data):
    cursor.execute(
        """
        INSERT INTO tblPCStatus (
            workstation_id, session_id, online_status, cpu_usage,
            ram_usage, storage_usage, network_status, camera_status,
            rfid_status, recorded_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            TIMESTAMPADD(
                SECOND, TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), CURRENT_TIMESTAMP()), %s
            )
        )
        """,
        (workstation_id, data["session_id"], data["online_status"],
         data["cpu_usage"], data["ram_usage"], data["storage_usage"],
         data["network_status"], data["camera_status"], data["rfid_status"], data["recorded_at"]),
    )
    return cursor.lastrowid


def monitoring_history_repo(cursor, workstation_id, limit, offset):
    if not inventory.get_inventory_repo(cursor, "workstations", workstation_id):
        raise DomainError("Workstation not found.", 404)
    cursor.execute(
        f"""
        SELECT {PC_COLUMNS}
        FROM tblPCStatus
        WHERE workstation_id = %s AND network_status IS NOT NULL
        ORDER BY tblPCStatus.recorded_at DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        (workstation_id, limit, offset),
    )
    return cursor.fetchall()


def dashboard_rows_repo(cursor, laboratory_id=None):
    query = """
        SELECT
            w.id AS workstation_id,
            w.laboratory_id,
            l.laboratory_name,
            l.status AS laboratory_status,
            w.pc_name,
            w.asset_tag,
            w.status,
            w.`condition`,
            ps.id AS pc_status_id,
            ps.online_status AS reported_online_status,
            TIMESTAMPADD(
                SECOND, TIMESTAMPDIFF(SECOND, CURRENT_TIMESTAMP(), UTC_TIMESTAMP()), ps.recorded_at
            ) AS last_heartbeat_at,
            ps.cpu_usage,
            ps.ram_usage,
            ps.storage_usage,
            ps.network_status,
            ps.camera_status,
            ps.rfid_status,
            (SELECT COUNT(*) FROM tblLaboratorySessions s
             WHERE s.workstation_id = w.id AND s.status = 'Active') AS active_session_count,
            (SELECT MIN(s.id) FROM tblLaboratorySessions s
             WHERE s.workstation_id = w.id AND s.status = 'Active') AS session_id,
            (SELECT COUNT(*) FROM tblRFIDReaders r
             WHERE r.workstation_id = w.id AND r.status = 'Active') AS reader_count,
            (SELECT COUNT(*) FROM tblArduinoDevices a
             WHERE a.workstation_id = w.id AND a.status = 'Active') AS arduino_count,
            (SELECT COUNT(*) FROM tblCameras c
             WHERE c.workstation_id = w.id AND c.status = 'Active') AS camera_count,
            (SELECT COUNT(*) FROM tblRFIDReaders r
             WHERE r.workstation_id = w.id AND
                (r.status <> 'Active' OR r.connection_status <> 'Connected')) AS unavailable_readers,
            (SELECT COUNT(*) FROM tblArduinoDevices a
             WHERE a.workstation_id = w.id AND
                (a.status <> 'Active' OR a.connection_status <> 'Connected')) AS unavailable_arduinos,
            (SELECT COUNT(*) FROM tblCameras c
             WHERE c.workstation_id = w.id AND
                (c.status <> 'Active' OR c.connection_status <> 'Connected')) AS unavailable_cameras
        FROM tblWorkstations w
        JOIN tblLaboratories l
            ON l.id = w.laboratory_id
        LEFT JOIN tblPCStatus ps
            ON ps.id = (
                SELECT latest.id
                FROM tblPCStatus latest
                WHERE latest.workstation_id = w.id AND latest.network_status IS NOT NULL
                ORDER BY latest.recorded_at DESC, latest.id DESC
                LIMIT 1
            )
    """
    params = []
    if laboratory_id is not None:
        if not inventory.get_inventory_repo(cursor, "laboratories", laboratory_id):
            raise DomainError("Laboratory not found.", 404)
        query += " WHERE w.laboratory_id = %s"
        params.append(laboratory_id)
    cursor.execute(query + " ORDER BY w.id", params)
    return cursor.fetchall()


def logs_repo(cursor, workstation_id, limit, offset):
    query = """
        SELECT
            id,
            workstation_id,
            log_level,
            source,
            message,
            created_at
        FROM tblSystemLogs
    """
    params = []
    if workstation_id is not None:
        query += " WHERE workstation_id = %s"
        params.append(workstation_id)
    cursor.execute(query + " ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
                   params + [limit, offset])
    return cursor.fetchall()


def active_student_details_repo(cursor):
    cursor.execute(
        """
        SELECT
            s.id AS session_id,
            s.student_id,
            student.student_number,
            u.first_name,
            u.last_name
        FROM tblLaboratorySessions s
        JOIN tblStudents student
            ON student.id = s.student_id
        JOIN tblUsers u
            ON u.id = student.user_id
        WHERE s.status = 'Active'
        """
    )
    return {row["session_id"]: row for row in cursor.fetchall()}
