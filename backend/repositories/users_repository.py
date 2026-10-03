from backend.database.connection import get_connection

def get_users_repo():
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.account_id,
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
                    u.date_disabled,
                    s.id AS student_id,
                    s.student_number,
                    s.program,
                    s.year_level,
                    s.section,
                    i.id AS instructor_id,
                    i.employee_number
                FROM tblUsers u
                INNER JOIN tblRoles r ON r.id = u.role_id
                LEFT JOIN tblStudents s ON s.user_id = u.id
                LEFT JOIN tblInstructors i ON i.user_id = u.id
                WHERE NOT r.role_name = 'Admin'
                """
            )
            users = cursor.fetchall() 

            for user in users:
                if user: 
                    user["created_at"] = user["created_at"].isoformat()
                    user["updated_at"] = user["updated_at"].isoformat()

            return users

    except Exception as e:
        print(f"Error: {e}")        
    finally:
        if conn: conn.close()


def get_user_by_id_repo(id):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.account_id,
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
                    u.date_disabled,
                    s.id AS student_id,
                    s.student_number,
                    s.program,
                    s.year_level,
                    s.section,
                    i.id AS instructor_id,
                    i.employee_number
                FROM tblUsers u
                INNER JOIN tblRoles r ON r.id = u.role_id
                LEFT JOIN tblStudents s ON s.user_id = u.id
                LEFT JOIN tblInstructors i ON i.user_id = u.id
                WHERE u.id = %s
                """,
                (id,)
            )
            user = cursor.fetchone()
            if user: 
                user["created_at"] = user["created_at"].isoformat()
                user["updated_at"] = user["updated_at"].isoformat()

            return user

    except Exception as e:
        print(f"Error: {e}")        
    finally:
        if conn: conn.close()




        