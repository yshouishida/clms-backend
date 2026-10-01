from backend.database.connection import get_connection

#===============================================
# GET ALL STUDENTS
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
                    s.user_id,
                    s.student_number,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.status AS user_status,
                    s.program,
                    s.year_level,
                    s.section
                FROM tblStudents AS s
                JOIN tblUsers AS u ON u.id = s.user_id;
                """
            )
            students = cursor.fetchall()

            return students
    except Exception as e:

        print(f"Error: {e}")
        
    finally:
        if conn: conn.close()

#===============================================
# GET BY ID STUDENTS
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
                    s.user_id,
                    s.student_number,
                    u.account_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    u.status AS user_status,
                    s.program,
                    s.year_level,
                    s.section
                FROM tblStudents AS s
                JOIN tblUsers AS u ON u.id = s.user_id
                WHERE s.student_id = %s
                """,
                (id,)
            )
            student = cursor.fetchone()

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

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tblUsers
                (
                    account_id, 
                    first_name, 
                    last_name, 
                    email, 
                    username, 
                    password_hash, 
                    role_id,
                    status,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active', NOW())
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
                INSERT INTO tblStudents
                (
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

            conn.commit()
            return True

    except Exception as e:
        if conn:conn
        print(f"Error: {e}")

    finally:
        if conn: conn.close()
        
#===============================================
# UPDATE STUDENT
#===============================================
def update_student_repo(        
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

        with conn.cursor() as cursor:
            cursor.execute(
                """

                """
            )

        return True 
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error: {e}")

    finally:
        if conn:conn.close()
        

#===============================================
# DELETE STUDENT
#===============================================