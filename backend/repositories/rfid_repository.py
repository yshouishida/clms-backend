from backend.database.connection import get_connection
from backend.utils.domain_error import DomainError


def list_cards_repo():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.card_uid,
                    c.status,
                    c.registered_at,
                    c.deactivated_at,
                    a.student_id,
                    s.student_number,
                    COALESCE(a.active_assignment_count, 0) AS active_assignment_count
                FROM tblRFIDCards c
                LEFT JOIN (
                    SELECT
                        rfid_id,
                        MIN(student_id) AS student_id,
                        COUNT(*) AS active_assignment_count
                    FROM tblRFIDAssignments
                    WHERE status = 'Active'
                    GROUP BY rfid_id
                ) a
                    ON a.rfid_id = c.id
                LEFT JOIN tblStudents s
                    ON s.id = a.student_id
                ORDER BY c.id
                """
            )

            return cursor.fetchall()

    finally:
        conn.close()


def register_card_repo(card_uid):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tblRFIDCards
                    (card_uid, status, registered_at)
                VALUES
                    (%s, 'Active', CURRENT_TIMESTAMP)
                """,
                (card_uid,)
            )
            card_id = cursor.lastrowid

        conn.commit()

        return {"card_id": card_id, "card_uid": card_uid, "status": "Active"}
    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def assign_card_repo(card_id, student_id):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id
                FROM tblStudents s
                JOIN tblUsers u
                    ON u.id = s.user_id
                JOIN tblRoles r
                    ON r.id = u.role_id
                WHERE s.id = %s AND u.status = 'Active' AND r.role_name = 'Student'
                FOR UPDATE
                """,
                (student_id,)
            )
            if not cursor.fetchone():
                raise DomainError("Active student not found.", 404)

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

            if not card:
                raise DomainError("RFID card not found.", 404)
            if card["status"] != "Active":
                raise DomainError("RFID card is not active.", 409)

            cursor.execute(
                """
                SELECT id
                FROM tblRFIDAssignments
                WHERE rfid_id = %s AND status = 'Active'
                LIMIT 1
                """,
                (card_id,)
            )
            if cursor.fetchone():
                raise DomainError("RFID card is already assigned.", 409)

            cursor.execute(
                """
                SELECT id
                FROM tblRFIDAssignments
                WHERE student_id = %s AND status = 'Active'
                LIMIT 1
                """,
                (student_id,)
            )
            if cursor.fetchone():
                raise DomainError("Student already has an active RFID card.", 409)

            cursor.execute(
                """
                INSERT INTO tblRFIDAssignments
                    (rfid_id, student_id, assigned_at, status)
                VALUES
                    (%s, %s, CURRENT_TIMESTAMP, 'Active')
                """,
                (card_id, student_id)
            )
            assignment_id = cursor.lastrowid

        conn.commit()

        return {"assignment_id": assignment_id, "card_id": card_id, "student_id": student_id}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def replace_card_repo(student_id, old_card_id, new_card_id):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
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

            if not student:
                raise DomainError("Student not found.", 404)
            if student["status"] != "Active" or student["role_name"] != "Student":
                raise DomainError("Student account is not active.", 409)

            cursor.execute(
                """
                SELECT
                    id,
                    status
                FROM tblRFIDCards
                WHERE id IN (%s, %s)
                ORDER BY id
                FOR UPDATE
                """,
                (old_card_id, new_card_id)
            )
            cards = {row["id"]: row for row in cursor.fetchall()}

            if len(cards) != 2:
                raise DomainError("Both RFID cards must be registered.", 404)
            if cards[new_card_id]["status"] != "Active":
                raise DomainError("Replacement card is not active.", 409)

            cursor.execute(
                """
                SELECT
                    id,
                    rfid_id
                FROM tblRFIDAssignments
                WHERE student_id = %s AND status = 'Active'
                """,
                (student_id,)
            )
            assignments = cursor.fetchall()

            if len(assignments) > 1 or (assignments and assignments[0]["rfid_id"] != old_card_id):
                raise DomainError("The student has a different active RFID card.", 409)

            if not assignments:
                if cards[old_card_id]["status"] == "Active":
                    raise DomainError("The old card is not actively assigned.", 409)

                cursor.execute(
                    """
                    SELECT id
                    FROM tblRFIDAssignments
                    WHERE rfid_id = %s AND student_id = %s AND status = 'Ended'
                    LIMIT 1
                    """,
                    (old_card_id, student_id)
                )
                if not cursor.fetchone():
                    raise DomainError("The old card was not assigned to this student.", 409)

            cursor.execute(
                """
                SELECT id
                FROM tblRFIDAssignments
                WHERE rfid_id = %s AND status = 'Active'
                LIMIT 1
                """,
                (new_card_id,)
            )
            if cursor.fetchone():
                raise DomainError("Replacement card is already assigned.", 409)

            if assignments:
                cursor.execute(
                    """
                    UPDATE tblRFIDAssignments
                    SET status = 'Ended',
                        unassigned_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (assignments[0]["id"],)
                )

            cursor.execute(
                """
                UPDATE tblRFIDCards
                SET status = CASE
                        WHEN status IN ('Lost', 'Damaged') THEN status
                        ELSE 'Disabled'
                    END,
                    deactivated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (old_card_id,)
            )
            cursor.execute(
                """
                INSERT INTO tblRFIDAssignments
                    (rfid_id, student_id, assigned_at, status)
                VALUES
                    (%s, %s, CURRENT_TIMESTAMP, 'Active')
                """,
                (new_card_id, student_id)
            )
            assignment_id = cursor.lastrowid

        conn.commit()

        return {
            "assignment_id": assignment_id,
            "student_id": student_id,
            "old_card_id": old_card_id,
            "new_card_id": new_card_id
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def set_card_status_repo(card_id, status):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM tblRFIDCards
                WHERE id = %s
                FOR UPDATE
                """,
                (card_id,)
            )
            card = cursor.fetchone()

            if not card:
                raise DomainError("RFID card not found.", 404)
            if status == "Active" and card["status"] in ("Lost", "Damaged"):
                raise DomainError("Lost or damaged cards cannot be reactivated.", 409)

            if status != "Active":
                cursor.execute(
                    """
                    UPDATE tblRFIDAssignments
                    SET status = 'Ended',
                        unassigned_at = CURRENT_TIMESTAMP
                    WHERE rfid_id = %s AND status = 'Active'
                    """,
                    (card_id,)
                )

            cursor.execute(
                """
                UPDATE tblRFIDCards
                SET status = %s,
                    deactivated_at = CASE
                        WHEN %s = 'Active' THEN NULL
                        ELSE CURRENT_TIMESTAMP
                    END
                WHERE id = %s
                """,
                (status, status, card_id)
            )

        conn.commit()

        return {"card_id": card_id, "status": status}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def card_history_repo(card_id):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM tblRFIDCards
                WHERE id = %s
                """,
                (card_id,)
            )
            if not cursor.fetchone():
                raise DomainError("RFID card not found.", 404)

            cursor.execute(
                """
                SELECT
                    a.id,
                    a.rfid_id,
                    a.student_id,
                    s.student_number,
                    a.assigned_at,
                    a.unassigned_at,
                    a.status
                FROM tblRFIDAssignments a
                JOIN tblStudents s
                    ON s.id = a.student_id
                WHERE a.rfid_id = %s
                ORDER BY a.assigned_at DESC, a.id DESC
                """,
                (card_id,)
            )
            return cursor.fetchall()

    finally:
        conn.close()
