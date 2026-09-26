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
                    s.id,
                    s.student_number,
                    u.first_name,
                    u.last_name,
                    s.program,
                    s.year_level,
                    s.section
                FROM tblStudents s
                INNER JOIN tblUsers u
                ON s.user_id = u.id
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
                    s.id,
                    s.student_number,
                    u.first_name,
                    u.last_name,
                    s.program,
                    s.year_level,
                    s.section
                FROM tblStudents s
                INNER JOIN tblUsers u
                ON s.user_id = u.id
                WHERE s.id = %s
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
def add_student_repo(student_number, program, year_level, section):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tblStudents
                (
                    student_number,
                    program,
                    year_level,
                    section
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    student_number,
                    program,
                    year_level,
                    section
                )
            )
            conn.commit()
            return True
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error: {e}")

    finally:
        if conn: conn.close()

#===============================================
# UPDATE STUDENT
#===============================================
def update_student_repo(student_number, program, year_level, section, id):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM tblStudents WHERE id = %s
                """,
                (id,)
            )
            if cursor.fetchone() is None:
                return False

            cursor.execute(
                """
                UPDATE tblStudents
                SET 
                    student_number,
                    program,
                    year_level,
                    section
                WHERE id = %s
                """,
                (
                    student_number, 
                    program, 
                    year_level, 
                    section, 
                    id
                )
            )
            conn.commit()
            return True

    except Exception as e:
        if conn:conn.rollback()
        print(f"Error: {e}")
        
    finally:
        if conn: conn.close()

#===============================================
# DELETE STUDENT
#===============================================