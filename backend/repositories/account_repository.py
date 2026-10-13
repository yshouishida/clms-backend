from backend.database.connection import get_connection
from backend.utils.domain_error import DomainError


def get_admins_repo():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.username,
                    u.status,
                    u.created_at,
                    u.updated_at,
                    u.date_disabled
                FROM tblUsers u
                JOIN tblRoles r
                    ON r.id = u.role_id
                WHERE r.role_name = 'Admin'
                ORDER BY u.id
                """
            )

            return cursor.fetchall()

    finally:
        conn.close()


def create_admin_repo(values, password_hash):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM tblRoles
                WHERE role_name = 'Admin'
                LIMIT 1
                """
            )
            role = cursor.fetchone()

            if not role:
                raise DomainError("Admin role is not configured.", 409)

            cursor.execute(
                """
                INSERT INTO tblUsers (
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    password_hash,
                    role_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    values["account_id"],
                    values["first_name"],
                    values["last_name"],
                    values["email"],
                    values["username"],
                    password_hash,
                    role["id"],
                ),
            )
            user_id = cursor.lastrowid

        conn.commit()
        return {"user_id": user_id, "role_name": "Admin"}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_admin_repo(user_id, values, password_hash=None):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id
                FROM tblUsers u
                JOIN tblRoles r
                    ON r.id = u.role_id
                WHERE u.id = %s AND r.role_name = 'Admin'
                FOR UPDATE
                """,
                (user_id,),
            )

            if not cursor.fetchone():
                raise DomainError("Administrator not found.", 404)

            cursor.execute(
                """
                UPDATE tblUsers
                SET account_id = %s,
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    username = %s
                WHERE id = %s
                """,
                (
                    values["account_id"],
                    values["first_name"],
                    values["last_name"],
                    values["email"],
                    values["username"],
                    user_id,
                ),
            )

            if password_hash is not None:
                cursor.execute(
                    """
                    UPDATE tblUsers
                    SET password_hash = %s
                    WHERE id = %s
                    """,
                    (password_hash, user_id),
                )

        conn.commit()
        return {"user_id": user_id, "role_name": "Admin"}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def set_account_status_repo(user_id, status):
    conn = get_connection()

    try:
        conn.begin()

        with conn.cursor() as cursor:
            # Workstations are the serialization points for session creation.
            cursor.execute(
                """
                SELECT
                    ls.workstation_id
                FROM tblLaboratorySessions ls
                JOIN tblStudents s
                    ON s.id = ls.student_id
                WHERE s.user_id = %s AND ls.status = 'Active'
                ORDER BY ls.workstation_id
                """,
                (user_id,),
            )

            workstation_ids = sorted({row["workstation_id"] for row in cursor.fetchall()})

            for workstation_id in workstation_ids:
                cursor.execute(
                    """
                    SELECT id
                    FROM tblWorkstations
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (workstation_id,),
                )
                cursor.fetchone()

            cursor.execute(
                """
                SELECT id, status
                FROM tblUsers
                WHERE id = %s
                FOR UPDATE
                """,
                (user_id,),
            )

            user = cursor.fetchone()

            if not user:
                raise DomainError("Account not found.", 404)

            if status == "Disabled":
                cursor.execute(
                    """
                    UPDATE tblLaboratorySessions ls
                    JOIN tblStudents s
                        ON s.id = ls.student_id
                    SET ls.status = 'Terminated',
                        ls.logout_at = CURRENT_TIMESTAMP
                    WHERE s.user_id = %s AND ls.status = 'Active'
                    """,
                    (user_id,),
                )

            cursor.execute(
                """
                UPDATE tblUsers
                SET
                    status = %s,
                    date_disabled = CASE
                        WHEN %s = 'Disabled'
                        THEN COALESCE(date_disabled, CURRENT_TIMESTAMP)
                        ELSE NULL
                    END
                WHERE id = %s
                """,
                (status, status, user_id),
            )

        conn.commit()
        return {"user_id": user_id, "status": status}

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
