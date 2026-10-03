from datetime import datetime
from backend.database.connection import get_connection


def login_repo(username):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    u.id,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.username,
                    u.password_hash,
                    u.status,
                    r.role_name,
                    s.student_number,
                    s.program,
                    s.year_level,
                    s.section,
                    i.employee_number
                FROM tblUsers u
                INNER JOIN tblRoles r
                    ON u.role_id = r.id
                LEFT JOIN tblStudents s
                    ON s.user_id = u.id
                LEFT JOIN tblInstructors i
                    ON i.user_id = u.id
                WHERE u.username = %s
                LIMIT 1
                """,
                (username,)
            )
            return cursor.fetchone()
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if conn: conn.close()

def record_auth_event_repo(
    user_id,
    action,
    entity_name,
    record_id=None,
    description=None,
    ip_address=None,
):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tblAuditLogs
                    (
                        user_id,
                        action,
                        entity_name,
                        record_id,
                        description,
                        ip_address,
                        created_at
                    )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    action,
                    entity_name,
                    record_id,
                    description,
                    ip_address,
                    datetime.now(),
                ),
            )

        conn.commit()
        return True

    except Exception as e:
        print(f"Error recording authentication event: {e}")

        if conn:
            conn.rollback()

        return False

    finally:
        if conn:
            conn.close()
            
