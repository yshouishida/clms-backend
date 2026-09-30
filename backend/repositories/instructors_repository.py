from backend.database.connection import get_connection


def get_instructiors_repo():
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    i.id AS instructor_id,
                    i.user_id,
                    i.employee_number,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.status AS user_status
                FROM tblInstructors AS i
                JOIN tblUsers AS u ON u.id = i.user_id
                """
            )

            return cursor.fetchall()
        
    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn: conn.close()

def get_by_id_repo(id):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    i.id AS instructor_id,
                    i.user_id,
                    i.employee_number,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.status AS user_status
                FROM tblInstructors AS i
                JOIN tblUsers AS u ON u.id = i.user_id
                WHERE i.id = %s
                """,
                (id,)
            )
            return cursor.fetchone()
        
    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn:conn.close()
        
