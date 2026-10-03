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
                    u.id AS user_id,
                    u.account_id,
                    i.employee_number,
                    u.first_name,
                    u.last_name,
                    TRIM(CONCAT_WS(' ', u.first_name, u.last_name)) AS full_name,
                    u.email,
                    u.username,
                    u.role_id,
                    r.role_name,
                    u.status AS account_status,
                    u.created_at,
                    u.updated_at,
                    u.date_disabled
                FROM tblInstructors i
                INNER JOIN tblUsers u ON u.id = i.user_id
                INNER JOIN tblRoles r ON r.id = u.role_id
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

def add_instructor_repo(
    account_id,
    first_name,
    last_name,
    email,
    username,
    password_hash,
    role_id,
    employee_number
):  
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tblUsers (
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    password_hash,
                    role_id,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')
                """,
                (
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    password_hash,
                    role_id
                )
            )
            user_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO tblInstructors (
                    user_id,
                    employee_number
                )
                VALUES (%s, %s)
                """,
                (
                    user_id,
                    employee_number
                )
            )

            instructor_id = cursor.lastrowid

        conn.commit()

        return {
            "user_id": user_id,
            "instructor_id": instructor_id
        }
    
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error: {e}")

    finally:
        if conn: conn.close()
        
