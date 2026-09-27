from backend.database.connection import get_connection



def login_repo(email):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor as cursor:
            cursor.execute(
                """
                SELECT 
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    password_hash,
                    role_id,
                    status
                FROM tblUsers
                WHERE email = %s
                """,
                (email,)
            )
            return cursor.fetchone()

        
    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn: conn.close()

def get_users_repo(id):
    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, 
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    password_hash,
                    role_id,
                    status
                FROM tblUsers
                WHERE id = %s
                """,
                (id,)
            )
            return cursor.fetchone()

    except Exception as e:
        print(f"Error: {e}")        
    finally:
        if conn: conn.close()
        



# account_id
# first_name
# last_name
# email
# username
# password_hash
# role_id
# status