from backend.database.connection import get_connection
from werkzeug.security import generate_password_hash


#=========================================
# CREATE A SUPER ADMIN 
#=========================================
def create_user():
    conn  = None

    account_id = "superadmin-001"
    first_name = "x1"
    last_name = "yshou"
    email = "super@admin.com"
    username = "x1"
    password = "asd"
    
    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            password_hash = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO tblUsers
                    (account_id, first_name, last_name, email, username, password_hash, role_id)
                VALUES 
                (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    account_id,
                    first_name,
                    last_name,
                    email,
                    username,
                    password_hash,
                    1
                )
            )
            conn.commit()
            print("CREATED!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

create_user()
