from backend.database.connection import get_connection
from backend.utils.domain_error import DomainError


def rfid_identity_repo(card_uid):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id AS card_id,
                    a.student_id,
                    u.id AS user_id,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.username,
                    s.student_number,
                    r.role_name
                FROM tblRFIDCards c
                JOIN tblRFIDAssignments a
                    ON a.rfid_id = c.id AND a.status = 'Active'
                JOIN tblStudents s
                    ON s.id = a.student_id
                JOIN tblUsers u
                    ON u.id = s.user_id
                JOIN tblRoles r
                    ON r.id = u.role_id
                WHERE c.card_uid = %s AND c.status = 'Active'
                    AND u.status = 'Active' AND r.role_name = 'Student'
                """,
                (card_uid,)
            )
            rows = cursor.fetchall()

            if len(rows) != 1:
                raise DomainError("RFID card is not eligible for login.", 401)

            return rows[0]

    finally:
        conn.close()


def create_session_repo(student_id, workstation_id, login_method, card_id=None, reader_id=None):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    w.id,
                    w.status,
                    w.`condition`,
                    l.status AS laboratory_status
                FROM tblWorkstations w
                JOIN tblLaboratories l
                    ON l.id = w.laboratory_id
                WHERE w.id = %s
                FOR UPDATE
                """,
                (workstation_id,)
            )
            workstation = cursor.fetchone()

            if not workstation:
                raise DomainError("Workstation not found.", 404)

            if (
                workstation["status"] != "Active"
                or workstation["condition"] != "Working"
                or workstation["laboratory_status"] != "Active"
            ):
                raise DomainError("Workstation is unavailable.", 409)

            cursor.execute(
                """
                SELECT
                    s.id,
                    u.status,
                    r.role_name
                FROM tblStudents s
                JOIN tblUsers u
                    ON u.id = s.user_id
                JOIN tblRoles r
                    ON r.id = u.role_id
                WHERE s.id = %s
                FOR UPDATE
                """,
                (student_id,)
            )
            student = cursor.fetchone()

            if not student or student["status"] != "Active" or student["role_name"] != "Student":
                raise DomainError("Student account is not active.", 401)

            if login_method == "RFID":
                cursor.execute(
                    """
                    SELECT
                        id,
                        status
                    FROM tblRFIDCards
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (card_id,)
                )
                card = cursor.fetchone()

                if not card or card["status"] != "Active":
                    raise DomainError("RFID card is not active.", 401)

                cursor.execute(
                    """
                    SELECT
                        rfid_id,
                        student_id
                    FROM tblRFIDAssignments
                    WHERE (rfid_id = %s OR student_id = %s) AND status = 'Active'
                    """,
                    (card_id, student_id)
                )
                assignments = cursor.fetchall()

                if (
                    len(assignments) != 1
                    or assignments[0]["rfid_id"] != card_id
                    or assignments[0]["student_id"] != student_id
                ):
                    raise DomainError("RFID assignment is not valid.", 401)

                cursor.execute(
                    """
                    SELECT id
                    FROM tblRFIDReaders
                    WHERE id = %s AND workstation_id = %s
                        AND status = 'Active' AND connection_status = 'Connected'
                    """,
                    (reader_id, workstation_id)
                )
                if not cursor.fetchone():
                    raise DomainError("RFID reader is not active at this workstation.", 409)

            cursor.execute(
                """
                SELECT id
                FROM tblLaboratorySessions
                WHERE status = 'Active' AND (workstation_id = %s OR student_id = %s)
                LIMIT 1
                """,
                (workstation_id, student_id)
            )
            if cursor.fetchone():
                raise DomainError("Student or workstation already has an active session.", 409)

            cursor.execute(
                """
                INSERT INTO tblLaboratorySessions
                    (student_id, workstation_id, rfid_id, login_method, login_at, status)
                VALUES
                    (%s, %s, %s, %s, CURRENT_TIMESTAMP, 'Active')
                """,
                (student_id, workstation_id, card_id, login_method)
            )
            session_id = cursor.lastrowid

        conn.commit()

        return {
            "session_id": session_id,
            "student_id": student_id,
            "workstation_id": workstation_id,
            "rfid_id": card_id,
            "login_method": login_method,
            "status": "Active"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def finish_session_repo(session_id, actor_user_id, actor_role, terminate=False):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT workstation_id
                FROM tblLaboratorySessions
                WHERE id = %s
                """,
                (session_id,)
            )
            preliminary = cursor.fetchone()

            if not preliminary:
                raise DomainError("Laboratory session not found.", 404)

            cursor.execute(
                """
                SELECT id
                FROM tblWorkstations
                WHERE id = %s
                FOR UPDATE
                """,
                (preliminary["workstation_id"],)
            )
            cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    ls.id,
                    ls.student_id,
                    ls.status,
                    u.id AS student_user_id
                FROM tblLaboratorySessions ls
                JOIN tblStudents s
                    ON s.id = ls.student_id
                JOIN tblUsers u
                    ON u.id = s.user_id
                WHERE ls.id = %s
                FOR UPDATE
                """,
                (session_id,)
            )
            session = cursor.fetchone()

            if actor_role != "Admin" and session["student_user_id"] != actor_user_id:
                raise DomainError("You cannot modify another student's session.", 403)
            if terminate and actor_role != "Admin":
                raise DomainError("Administrator access is required.", 403)

            if session["status"] != "Active":
                conn.rollback()
                return {"session_id": session_id, "status": session["status"], "already_finished": True}

            new_status = "Terminated" if terminate else "Completed"
            cursor.execute(
                """
                UPDATE tblLaboratorySessions
                SET status = %s,
                    logout_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_status, session_id)
            )

        conn.commit()

        return {"session_id": session_id, "status": new_status, "already_finished": False}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def heartbeat_session_repo(session_id, actor_user_id):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ls.workstation_id,
                    ls.status,
                    u.id AS student_user_id
                FROM tblLaboratorySessions ls
                JOIN tblStudents s
                    ON s.id = ls.student_id
                JOIN tblUsers u
                    ON u.id = s.user_id
                WHERE ls.id = %s
                FOR UPDATE
                """,
                (session_id,)
            )
            session = cursor.fetchone()

            if not session:
                raise DomainError("Laboratory session not found.", 404)
            if session["student_user_id"] != actor_user_id:
                raise DomainError("You cannot update another student's session.", 403)
            if session["status"] != "Active":
                raise DomainError("Laboratory session is not active.", 409)

            cursor.execute(
                """
                INSERT INTO tblPCStatus
                    (workstation_id, session_id, online_status, recorded_at)
                VALUES
                    (%s, %s, 'Online', CURRENT_TIMESTAMP)
                """,
                (session["workstation_id"], session_id)
            )
            pc_status_id = cursor.lastrowid

        conn.commit()

        return {"session_id": session_id, "pc_status_id": pc_status_id}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def session_history_repo(actor_user_id, actor_role, active_only=False):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    ls.id AS session_id,
                    ls.student_id,
                    s.student_number,
                    ls.workstation_id,
                    w.pc_name,
                    w.laboratory_id,
                    ls.rfid_id,
                    ls.login_method,
                    ls.login_at,
                    ls.logout_at,
                    ls.status
                FROM tblLaboratorySessions ls
                JOIN tblStudents s
                    ON s.id = ls.student_id
                JOIN tblUsers u
                    ON u.id = s.user_id
                JOIN tblWorkstations w
                    ON w.id = ls.workstation_id
                WHERE 1 = 1
            """
            params = []

            if actor_role != "Admin":
                sql += " AND u.id = %s"
                params.append(actor_user_id)

            if active_only:
                sql += " AND ls.status = 'Active'"

            sql += " ORDER BY ls.login_at DESC, ls.id DESC"
            cursor.execute(sql, params)

            return cursor.fetchall()

    finally:
        conn.close()


def recovery_candidates_repo(minutes):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ls.id AS session_id,
                    ls.student_id,
                    s.student_number,
                    ls.workstation_id,
                    w.pc_name,
                    ls.login_at,
                    TIMESTAMPDIFF(MINUTE, ls.login_at, CURRENT_TIMESTAMP) AS active_minutes,
                    ps.recorded_at AS last_pc_status_at,
                    ps.online_status AS last_online_status
                FROM tblLaboratorySessions ls
                JOIN tblStudents s
                    ON s.id = ls.student_id
                JOIN tblWorkstations w
                    ON w.id = ls.workstation_id
                LEFT JOIN tblPCStatus ps
                    ON ps.id = (
                        SELECT latest.id
                        FROM tblPCStatus latest
                        WHERE latest.session_id = ls.id
                        ORDER BY latest.recorded_at DESC, latest.id DESC
                        LIMIT 1
                    )
                WHERE ls.status = 'Active'
                    AND (
                        ps.online_status = 'Offline'
                        OR COALESCE(ps.recorded_at, ls.login_at)
                            <= CURRENT_TIMESTAMP - INTERVAL %s MINUTE
                    )
                ORDER BY ls.login_at, ls.id
                """,
                (minutes,)
            )
            return cursor.fetchall()

    finally:
        conn.close()


def usage_summary_repo():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id AS student_id,
                    s.student_number,
                    COUNT(*) AS session_count,
                    CAST(
                        SUM(CASE WHEN ls.status = 'Active' THEN 1 ELSE 0 END)
                        AS UNSIGNED
                    ) AS active_count,
                    CAST(
                        COALESCE(
                            SUM(
                                CASE
                                    WHEN ls.status IN ('Completed', 'Terminated')
                                        AND ls.logout_at IS NOT NULL
                                    THEN GREATEST(
                                        TIMESTAMPDIFF(SECOND, ls.login_at, ls.logout_at),
                                        0
                                    )
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS UNSIGNED
                    ) AS total_seconds
                FROM tblStudents s
                JOIN tblLaboratorySessions ls
                    ON ls.student_id = s.id
                GROUP BY s.id, s.student_number
                ORDER BY s.id
                """
            )
            return cursor.fetchall()

    finally:
        conn.close()
