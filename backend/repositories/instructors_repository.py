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
                WHERE r.role_name = 'Instructor'
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
        conn.begin()

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

    except Exception:
        if conn is not None:
            conn.rollback()

        raise

    finally:
        if conn is not None:
            conn.close()

#===============================================
# UPDATE INSTRUCTOR
#===============================================
def update_instructor_repo(
    instructor_id,
    account_id,
    first_name,
    last_name,
    email,
    username,
    employee_number
):
    conn = None

    try:
        conn = get_connection()
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.user_id
                FROM tblInstructors i
                INNER JOIN tblUsers u ON u.id = i.user_id
                WHERE i.id = %s
                FOR UPDATE
                """,
                (instructor_id,)
            )

            instructor = cursor.fetchone()

            if instructor is None:
                conn.rollback()
                return None

            user_id = instructor["user_id"]

            cursor.execute(
                """
                UPDATE tblUsers
                SET
                    account_id = %s,
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    username = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    user_id
                )
            )

            cursor.execute(
                """
                UPDATE tblInstructors
                SET employee_number = %s
                WHERE id = %s
                """,
                (
                    employee_number,
                    instructor_id
                )
            )

        conn.commit()

        return {
            "user_id": user_id,
            "instructor_id": instructor_id
        }

    except Exception:
        if conn is not None:
            conn.rollback()

        raise

    finally:
        if conn is not None:
            conn.close()


#===============================================
# SOFT DELETE INSTRUCTOR
#===============================================
def delete_instructor_repo(instructor_id):
    conn = None

    try:
        conn = get_connection()
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    i.user_id,
                    u.status
                FROM tblInstructors i
                INNER JOIN tblUsers u ON u.id = i.user_id
                WHERE i.id = %s
                FOR UPDATE
                """,
                (instructor_id,)
            )

            instructor = cursor.fetchone()

            if instructor is None:
                conn.rollback()
                return None

            user_id = instructor["user_id"]

            # Preserve the original date if already disabled.
            if instructor["status"] == "Active":
                cursor.execute(
                    """
                    UPDATE tblUsers
                    SET
                        status = 'Disabled',
                        date_disabled = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (user_id,)
                )

        conn.commit()

        return {
            "user_id": user_id,
            "instructor_id": instructor_id,
            "account_status": "Disabled"
        }

    except Exception:
        if conn is not None:
            conn.rollback()

        raise

    finally:
        if conn is not None:
            conn.close()
