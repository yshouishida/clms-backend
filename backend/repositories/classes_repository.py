def get_instructor_profile_repo(cursor, user_id):
    cursor.execute(
        """
        SELECT i.id AS instructor_id
        FROM tblInstructors i
        INNER JOIN tblUsers u ON u.id = i.user_id
        INNER JOIN tblRoles r ON r.id = u.role_id
        WHERE i.user_id = %s
          AND u.status = 'Active'
          AND r.role_name = 'Instructor'
        """,
        (user_id,),
    )
    return cursor.fetchone()


def get_student_profile_repo(cursor, user_id):
    cursor.execute(
        """
        SELECT s.id AS student_id
        FROM tblStudents s
        INNER JOIN tblUsers u ON u.id = s.user_id
        INNER JOIN tblRoles r ON r.id = u.role_id
        WHERE s.user_id = %s
          AND u.status = 'Active'
          AND r.role_name = 'Student'
        """,
        (user_id,),
    )
    return cursor.fetchone()


def list_classes_repo(cursor, role, profile_id=None):
    if role == "Instructor":
        cursor.execute(
            """
            SELECT id, instructor_id, class_code, class_name,
                   description, school_year, semester, status, created_at
            FROM tblClasses
            WHERE instructor_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (profile_id,),
        )
    elif role == "Student":
        cursor.execute(
            """
            SELECT c.id, c.instructor_id, c.class_code, c.class_name,
                   c.description, c.school_year, c.semester, c.status,
                   c.created_at, cm.status AS membership_status,
                   cm.enrolled_at
            FROM tblClassMembers cm
            INNER JOIN tblClasses c ON c.id = cm.class_id
            WHERE cm.student_id = %s
              AND cm.status = 'Enrolled'
            ORDER BY c.created_at DESC, c.id DESC
            """,
            (profile_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, instructor_id, class_code, class_name,
                   description, school_year, semester, status, created_at
            FROM tblClasses
            ORDER BY created_at DESC, id DESC
            """
        )
    return cursor.fetchall()


def get_class_repo(cursor, class_id, role, profile_id=None):
    if role == "Instructor":
        cursor.execute(
            """
            SELECT id, instructor_id, class_code, class_name,
                   description, school_year, semester, status, created_at
            FROM tblClasses
            WHERE id = %s AND instructor_id = %s
            """,
            (class_id, profile_id),
        )
    elif role == "Student":
        cursor.execute(
            """
            SELECT c.id, c.instructor_id, c.class_code, c.class_name,
                   c.description, c.school_year, c.semester, c.status,
                   c.created_at, cm.status AS membership_status,
                   cm.enrolled_at
            FROM tblClasses c
            INNER JOIN tblClassMembers cm ON cm.class_id = c.id
            WHERE c.id = %s
              AND cm.student_id = %s
              AND cm.status = 'Enrolled'
            """,
            (class_id, profile_id),
        )
    else:
        cursor.execute(
            """
            SELECT id, instructor_id, class_code, class_name,
                   description, school_year, semester, status, created_at
            FROM tblClasses
            WHERE id = %s
            """,
            (class_id,),
        )
    return cursor.fetchone()


def class_code_exists_repo(
    cursor, class_code, school_year, semester, instructor_id, exclude_id=None
):
    query = """
        SELECT id
        FROM tblClasses
        WHERE class_code = %s
          AND school_year = %s
          AND semester = %s
          AND instructor_id = %s
    """
    params = [class_code, school_year, semester, instructor_id]

    if exclude_id is not None:
        query += " AND id <> %s"
        params.append(exclude_id)

    query += " LIMIT 1"
    cursor.execute(query, tuple(params))
    return cursor.fetchone() is not None


def insert_class_repo(cursor, instructor_id, fields):
    cursor.execute(
        """
        INSERT INTO tblClasses (
            instructor_id, class_code, class_name, description,
            school_year, semester, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """,
        (
            instructor_id,
            fields["class_code"],
            fields["class_name"],
            fields["description"],
            fields["school_year"],
            fields["semester"],
        ),
    )
    return cursor.lastrowid


def update_class_repo(cursor, class_id, instructor_id, fields, is_admin):
    query = """
        UPDATE tblClasses
        SET class_code = %s,
            class_name = %s,
            description = %s,
            school_year = %s,
            semester = %s
        WHERE id = %s
    """
    params = [
        fields["class_code"],
        fields["class_name"],
        fields["description"],
        fields["school_year"],
        fields["semester"],
        class_id,
    ]

    if not is_admin:
        query += " AND instructor_id = %s"
        params.append(instructor_id)

    cursor.execute(query, tuple(params))
    return cursor.rowcount > 0


def archive_class_repo(cursor, class_id, instructor_id, is_admin):
    query = "UPDATE tblClasses SET status = 'Archived' WHERE id = %s"
    params = [class_id]

    if not is_admin:
        query += " AND instructor_id = %s"
        params.append(instructor_id)

    cursor.execute(query, tuple(params))
    return cursor.rowcount > 0


def student_is_active_repo(cursor, student_id):
    cursor.execute(
        """
        SELECT s.id
        FROM tblStudents s
        INNER JOIN tblUsers u ON u.id = s.user_id
        WHERE s.id = %s AND u.status = 'Active'
        """,
        (student_id,),
    )
    return cursor.fetchone() is not None


def list_class_members_repo(cursor, class_id):
    cursor.execute(
        """
        SELECT cm.id, cm.class_id, cm.student_id, cm.enrolled_at,
               cm.status, s.student_number, u.first_name, u.last_name
        FROM tblClassMembers cm
        INNER JOIN tblStudents s ON s.id = cm.student_id
        INNER JOIN tblUsers u ON u.id = s.user_id
        WHERE cm.class_id = %s
        ORDER BY u.last_name, u.first_name, cm.id
        """,
        (class_id,),
    )
    return cursor.fetchall()


def get_class_member_repo(cursor, class_id, student_id):
    cursor.execute(
        """
        SELECT id, class_id, student_id, enrolled_at, status
        FROM tblClassMembers
        WHERE class_id = %s AND student_id = %s
        """,
        (class_id, student_id),
    )
    return cursor.fetchone()


def insert_class_member_repo(cursor, class_id, student_id):
    cursor.execute(
        """
        INSERT INTO tblClassMembers (class_id, student_id, enrolled_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        """,
        (class_id, student_id),
    )
    return cursor.lastrowid


def update_class_member_repo(cursor, class_id, student_id, status):
    if status == "Enrolled":
        cursor.execute(
            """
            UPDATE tblClassMembers
            SET status = %s, enrolled_at = CURRENT_TIMESTAMP
            WHERE class_id = %s AND student_id = %s
            """,
            (status, class_id, student_id),
        )
    else:
        cursor.execute(
            """
            UPDATE tblClassMembers
            SET status = %s
            WHERE class_id = %s AND student_id = %s
            """,
            (status, class_id, student_id),
        )
    return cursor.rowcount > 0