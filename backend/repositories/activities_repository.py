def list_activities_repo(cursor, class_id, role, profile_id=None):
    if role == "Student":
        cursor.execute(
            """
            SELECT a.id, a.class_id, a.instructor_id, a.activity_name,
                   a.instructions, a.due_date, a.created_at, a.status
            FROM tblActivities a
            INNER JOIN tblClassMembers cm ON cm.class_id = a.class_id
            WHERE a.class_id = %s
              AND cm.student_id = %s
              AND cm.status = 'Enrolled'
              AND a.status IN ('Published', 'Closed')
            ORDER BY a.due_date, a.id
            """,
            (class_id, profile_id),
        )
    elif role == "Instructor":
        cursor.execute(
            """
            SELECT id, class_id, instructor_id, activity_name,
                   instructions, due_date, created_at, status
            FROM tblActivities
            WHERE class_id = %s AND instructor_id = %s
            ORDER BY due_date, id
            """,
            (class_id, profile_id),
        )
    else:
        cursor.execute(
            """
            SELECT id, class_id, instructor_id, activity_name,
                   instructions, due_date, created_at, status
            FROM tblActivities
            WHERE class_id = %s
            ORDER BY due_date, id
            """,
            (class_id,),
        )
    return cursor.fetchall()


def get_activity_repo(cursor, activity_id, role, profile_id=None):
    if role == "Student":
        cursor.execute(
            """
            SELECT a.id, a.class_id, a.instructor_id, a.activity_name,
                   a.instructions, a.due_date, a.created_at, a.status
            FROM tblActivities a
            INNER JOIN tblClassMembers cm ON cm.class_id = a.class_id
            WHERE a.id = %s
              AND cm.student_id = %s
              AND cm.status = 'Enrolled'
              AND a.status IN ('Published', 'Closed')
            """,
            (activity_id, profile_id),
        )
    elif role == "Instructor":
        cursor.execute(
            """
            SELECT id, class_id, instructor_id, activity_name,
                   instructions, due_date, created_at, status
            FROM tblActivities
            WHERE id = %s AND instructor_id = %s
            """,
            (activity_id, profile_id),
        )
    else:
        cursor.execute(
            """
            SELECT id, class_id, instructor_id, activity_name,
                   instructions, due_date, created_at, status
            FROM tblActivities
            WHERE id = %s
            """,
            (activity_id,),
        )
    return cursor.fetchone()


def insert_activity_repo(cursor, class_id, instructor_id, fields):
    cursor.execute(
        """
        INSERT INTO tblActivities (
            class_id, instructor_id, activity_name, instructions,
            due_date, created_at, status
        )
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'Draft')
        """,
        (
            class_id,
            instructor_id,
            fields["activity_name"],
            fields["instructions"],
            fields["due_date"],
        ),
    )
    return cursor.lastrowid


def update_activity_repo(cursor, activity_id, fields):
    cursor.execute(
        """
        UPDATE tblActivities
        SET activity_name = %s,
            instructions = %s,
            due_date = %s
        WHERE id = %s
        """,
        (
            fields["activity_name"],
            fields["instructions"],
            fields["due_date"],
            activity_id,
        ),
    )
    return cursor.rowcount > 0


def update_activity_status_repo(cursor, activity_id, status):
    cursor.execute(
        "UPDATE tblActivities SET status = %s WHERE id = %s",
        (status, activity_id),
    )
    return cursor.rowcount > 0