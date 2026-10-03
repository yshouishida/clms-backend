from backend.database.connection import get_connection

#===============================================
# GET STUDENTS
#===============================================
def get_students_repo():
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id AS student_id,
                    u.id AS user_id,
                    u.account_id,
                    s.student_number,
                    u.first_name,
                    u.last_name,
                    TRIM(CONCAT_WS(' ', u.first_name, u.last_name)) AS full_name,
                    u.email,
                    u.username,
                    s.program,
                    s.year_level,
                    s.section,
                    u.role_id,
                    r.role_name,
                    u.status AS account_status,
                    u.created_at,
                    u.updated_at,
                    u.date_disabled
                FROM tblStudents s
                INNER JOIN tblUsers u ON u.id = s.user_id
                INNER JOIN tblRoles r ON r.id = u.role_id
                WHERE NOT r.role_name = 'Admin'
                """
            )
            students = cursor.fetchall()

            for student in students:
                if student:
                    student["created_at"] = student["created_at"].isoformat()
                    student["updated_at"] = student["updated_at"].isoformat()

            return students
    except Exception as e:

        print(f"Error: {e}")
        
    finally:
        if conn: conn.close()

#===============================================
# GET STUDENTS BY ID
#===============================================
def get_by_id_repo(id):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id AS student_id,
                    u.id AS user_id,
                    u.account_id,
                    s.student_number,
                    u.first_name,
                    u.last_name,
                    TRIM(CONCAT_WS(' ', u.first_name, u.last_name)) AS full_name,
                    u.email,
                    u.username,
                    s.program,
                    s.year_level,
                    s.section,
                    u.role_id,
                    r.role_name,
                    u.status AS account_status,
                    u.created_at,
                    u.updated_at,
                    u.date_disabled
                FROM tblStudents s
                INNER JOIN tblUsers u ON u.id = s.user_id
                INNER JOIN tblRoles r ON r.id = u.role_id
                WHERE s.id = %s AND NOT r.role_name = 'Admin'
                """,
                (id,)
            )
            student = cursor.fetchone()

            if student:
                student["created_at"] = student["created_at"].isoformat()
                student["updated_at"] = student["updated_at"].isoformat()

            return student
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:conn.close()

#===============================================
# ADD STUDENT
#===============================================
def add_student_repo(
    account_id,
    first_name,
    last_name,
    email,
    username,
    password_hash,
    role_id,
    student_number,
    program,
    year_level,
    section
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
                INSERT INTO tblStudents (
                    user_id,
                    student_number,
                    program,
                    year_level,
                    section
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    student_number,
                    program,
                    year_level,
                    section
                )
            )

            student_id = cursor.lastrowid

        conn.commit()

        return {
            "user_id": user_id,
            "student_id": student_id
        }
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error: {e}")

    finally:
        if conn: conn.close()
        

#===============================================
# UPDATE STUDENT
#===============================================
def update_student_repo(
    student_id,
    account_id,
    first_name,
    last_name,
    email,
    username,
    student_number,
    program,
    year_level,
    section
):
    conn = None

    try:
        conn = get_connection()
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.user_id
                FROM tblStudents s
                INNER JOIN tblUsers u ON u.id = s.user_id
                WHERE s.id = %s
                FOR UPDATE
                """,
                (student_id,)
            )

            student = cursor.fetchone()

            if student is None:
                conn.rollback()
                return None

            user_id = student["user_id"]

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
                UPDATE tblStudents
                SET
                    student_number = %s,
                    program = %s,
                    year_level = %s,
                    section = %s
                WHERE id = %s
                """,
                (
                    student_number,
                    program,
                    year_level,
                    section,
                    student_id
                )
            )

        conn.commit()

        return {
            "user_id": user_id,
            "student_id": student_id
        }

    except Exception:
        if conn is not None:
            conn.rollback()

        raise

    finally:
        if conn is not None:
            conn.close()


#===============================================
# DELETE STUDENT
#===============================================
def delete_student_repo(student_id):
    conn = None

    try:
        conn = get_connection()
        conn.begin()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.user_id,
                    u.status
                FROM tblStudents s
                INNER JOIN tblUsers u ON u.id = s.user_id
                WHERE s.id = %s
                FOR UPDATE
                """,
                (student_id,)
            )

            student = cursor.fetchone()

            if student is None:
                conn.rollback()
                return None

            user_id = student["user_id"]

            # Preserve the original date if already disabled.
            if student["status"] == "Active":
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
            "student_id": student_id,
            "account_status": "Disabled"
        }

    except Exception:
        if conn is not None:
            conn.rollback()

        raise

    finally:
        if conn is not None:
            conn.close()
