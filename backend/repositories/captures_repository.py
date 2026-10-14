from backend.utils.domain_error import DomainError


def capture_session_repo(cursor, workstation_id, session_id, camera_id):
    cursor.execute(
        """
        SELECT
            s.id,
            s.workstation_id,
            s.login_at,
            s.status,
            TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), CURRENT_TIMESTAMP()) AS utc_offset
        FROM tblLaboratorySessions s
        WHERE s.id = %s
        FOR UPDATE
        """,
        (session_id,),
    )
    session = cursor.fetchone()
    if not session or session["workstation_id"] != workstation_id:
        raise DomainError("Session does not belong to this workstation.", 409)
    if session["status"] != "Active":
        raise DomainError("Session is no longer active.", 409)
    cursor.execute(
        """
        SELECT
            id,
            workstation_id,
            status,
            connection_status
        FROM tblCameras
        WHERE id = %s
        FOR UPDATE
        """,
        (camera_id,),
    )
    camera = cursor.fetchone()
    if not camera or camera["workstation_id"] != workstation_id:
        raise DomainError("Camera does not belong to this workstation.", 409)
    return session, camera


def existing_capture_repo(cursor, session_id, camera_id, status):
    cursor.execute(
        """
        SELECT
            id,
            file_path,
            captured_at,
            capture_status
        FROM tblCameraCaptures
        WHERE session_id = %s AND camera_id = %s AND capture_status = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (session_id, camera_id, status),
    )
    return cursor.fetchone()


def insert_capture_repo(cursor, session_id, camera_id, filename, captured_at, status):
    cursor.execute(
        """
        INSERT INTO tblCameraCaptures
            (session_id, camera_id, file_path, captured_at, capture_status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (session_id, camera_id, filename, captured_at, status),
    )
    return cursor.lastrowid


def stored_capture_exists_repo(cursor, filename):
    cursor.execute(
        """
        SELECT
            id
        FROM tblCameraCaptures
        WHERE file_path = %s AND capture_status = 'Captured'
        LIMIT 1
        """,
        (filename,),
    )
    return cursor.fetchone() is not None


def capture_metadata_repo(cursor, capture_id, user_id, role):
    cursor.execute(
        """
        SELECT
            c.id,
            c.session_id,
            c.camera_id,
            c.file_path,
            c.captured_at,
            c.capture_status,
            s.workstation_id,
            s.student_id,
            student.user_id
        FROM tblCameraCaptures c
        JOIN tblLaboratorySessions s
            ON s.id = c.session_id
        JOIN tblStudents student
            ON student.id = s.student_id
        WHERE c.id = %s
        """,
        (capture_id,),
    )
    row = cursor.fetchone()
    if not row or (role != "Admin" and row["user_id"] != user_id):
        raise DomainError("Camera capture not found.", 404)
    return row


def list_captures_repo(cursor, user_id, role, limit, offset, session_id=None):
    query = """
        SELECT
            c.id,
            c.session_id,
            c.camera_id,
            c.captured_at,
            c.capture_status,
            s.workstation_id,
            s.student_id
        FROM tblCameraCaptures c
        JOIN tblLaboratorySessions s
            ON s.id = c.session_id
        JOIN tblStudents student
            ON student.id = s.student_id
        WHERE (%s = 'Admin' OR student.user_id = %s)
    """
    params = [role, user_id]
    if session_id is not None:
        query += " AND c.session_id = %s"
        params.append(session_id)
    cursor.execute(query + " ORDER BY c.captured_at DESC, c.id DESC LIMIT %s OFFSET %s",
                   params + [limit, offset])
    return cursor.fetchall()


def capture_summary_repo(cursor):
    cursor.execute(
        """
        SELECT
            s.workstation_id,
            c.camera_id,
            c.capture_status,
            COUNT(*) AS capture_count
        FROM tblCameraCaptures c
        JOIN tblLaboratorySessions s
            ON s.id = c.session_id
        GROUP BY s.workstation_id, c.camera_id, c.capture_status
        ORDER BY s.workstation_id, c.camera_id, c.capture_status
        """
    )
    return cursor.fetchall()
