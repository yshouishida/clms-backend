def lock_activity_repo(cursor, activity_id):
    cursor.execute(
        """
        SELECT id, class_id, instructor_id, due_date, status
        FROM tblActivities
        WHERE id = %s
        FOR UPDATE
        """,
        (activity_id,),
    )
    return cursor.fetchone()


def student_membership_repo(cursor, class_id, user_id):
    cursor.execute(
        """
        SELECT s.id AS student_id
        FROM tblStudents s
        JOIN tblUsers u ON u.id = s.user_id
        JOIN tblRoles r ON r.id = u.role_id
        JOIN tblClassMembers cm ON cm.student_id = s.id
        WHERE u.id = %s AND u.status = 'Active'
          AND r.role_name = 'Student'
          AND cm.class_id = %s AND cm.status = 'Enrolled'
        FOR UPDATE
        """,
        (user_id, class_id),
    )
    return cursor.fetchone()


def owned_project_repo(cursor, project_id, student_id):
    cursor.execute(
        """
        SELECT id, student_id, folder_id, status, deleted_at
        FROM tblProjects
        WHERE id = %s AND student_id = %s
        FOR UPDATE
        """,
        (project_id, student_id),
    )
    project = cursor.fetchone()
    if not project or project["status"] != "Active" or project["deleted_at"] is not None:
        return None
    return project


def owned_project_files_repo(cursor, project_id, student_id, file_ids):
    placeholders = ", ".join(["%s"] * len(file_ids))
    cursor.execute(
        f"""
        SELECT
            f.id,
            f.project_id,
            f.file_name,
            f.file_type,
            f.file_size,
            f.current_path,
            f.status,
            f.deleted_at
        FROM tblProjectFiles f
        JOIN tblProjects p ON p.id = f.project_id
        WHERE f.project_id = %s AND p.student_id = %s
          AND p.status = 'Active' AND p.deleted_at IS NULL
          AND f.status = 'Active' AND f.deleted_at IS NULL
          AND f.id IN ({placeholders})
        ORDER BY f.id
        FOR UPDATE
        """,
        (project_id, student_id, *file_ids),
    )
    return cursor.fetchall()


def submission_repo(cursor, activity_id, student_id, lock=False):
    cursor.execute(
        """
        SELECT id, activity_id, student_id, project_id, submitted_at, status, remarks
        FROM tblSubmissions
        WHERE activity_id = %s AND student_id = %s
        """ + (" FOR UPDATE" if lock else ""),
        (activity_id, student_id),
    )
    return cursor.fetchone()


def create_submission_repo(cursor, activity_id, student_id, project_id, status):
    cursor.execute(
        """
        INSERT INTO tblSubmissions
            (activity_id, student_id, project_id, submitted_at, status)
        VALUES (%s, %s, %s, UTC_TIMESTAMP(), %s)
        """,
        (activity_id, student_id, project_id, status),
    )
    return cursor.lastrowid


def update_submission_repo(cursor, submission_id, project_id, status):
    cursor.execute(
        """
        UPDATE tblSubmissions
        SET project_id = %s, submitted_at = UTC_TIMESTAMP(),
            status = %s, remarks = NULL
        WHERE id = %s
        """,
        (project_id, status, submission_id),
    )


def update_submission_review_state_repo(cursor, submission_id, status, remarks):
    cursor.execute(
        """
        UPDATE tblSubmissions
        SET status = %s, remarks = %s
        WHERE id = %s
        """,
        (status, remarks, submission_id),
    )





def insert_submission_snapshot_file_repo(
    cursor, project_id, folder_id, file_name, file_type, file_size, file_path
):
    cursor.execute(
        """
        INSERT INTO tblProjectFiles
            (project_id, folder_id, file_name, file_type, file_size,
             current_path, created_at, updated_at, deleted_at, status)
        VALUES (%s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP(),
                UTC_TIMESTAMP(), 'Archived')
        """,
        (project_id, folder_id, file_name, file_type, file_size, file_path),
    )
    return cursor.lastrowid


def insert_project_version_repo(cursor, file, user_id, version_number):
    cursor.execute(
        """
        INSERT INTO tblProjectVersions
            (file_id, version_number, file_path, file_size, created_by, created_at)
        VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP())
        """,
        (file["id"], version_number, file["current_path"], file["file_size"], user_id),
    )
    return cursor.lastrowid


def replace_submission_files_repo(cursor, submission_id, snapshot_file_ids):
    cursor.execute(
        "DELETE FROM tblSubmissionFiles WHERE submission_id = %s",
        (submission_id,),
    )
    for file_id in snapshot_file_ids:
        cursor.execute(
            "INSERT INTO tblSubmissionFiles (submission_id, file_id) VALUES (%s, %s)",
            (submission_id, file_id),
        )


def list_activity_submissions_repo(cursor, activity_id, role, profile_id):
    query = """
        SELECT
            s.id AS submission_id,
            s.activity_id,
            s.student_id,
            s.project_id,
            s.submitted_at,
            s.status,
            s.remarks,
            st.student_number,
            u.first_name,
            u.last_name
        FROM tblSubmissions s
        JOIN tblStudents st ON st.id = s.student_id
        JOIN tblUsers u ON u.id = st.user_id
        JOIN tblActivities a ON a.id = s.activity_id
        WHERE s.activity_id = %s
    """
    params = [activity_id]
    if role == "Instructor":
        query += " AND a.instructor_id = %s"
        params.append(profile_id)
    elif role == "Student":
        query += " AND s.student_id = %s"
        params.append(profile_id)
    cursor.execute(query + " ORDER BY s.submitted_at DESC, s.id DESC", params)
    return cursor.fetchall()


def submission_access_repo(cursor, submission_id):
    cursor.execute(
        """
        SELECT
            s.id AS submission_id,
            s.activity_id,
            s.student_id,
            s.project_id,
            s.submitted_at,
            s.status,
            s.remarks,
            a.instructor_id,
            st.user_id
        FROM tblSubmissions s
        JOIN tblActivities a ON a.id = s.activity_id
        JOIN tblStudents st ON st.id = s.student_id
        WHERE s.id = %s
        """,
        (submission_id,),
    )
    return cursor.fetchone()


def lock_submission_repo(cursor, submission_id):
    cursor.execute(
        "SELECT id FROM tblSubmissions WHERE id = %s FOR UPDATE",
        (submission_id,),
    )
    return cursor.fetchone()


def list_submission_files_repo(cursor, submission_id):
    cursor.execute(
        """
        SELECT
            sf.id AS submission_file_id,
            f.id AS file_id,
            f.file_name,
            f.file_type,
            f.file_size,
            pv.id AS project_version_id,
            pv.version_number AS file_version
        FROM tblSubmissionFiles sf
        JOIN tblProjectFiles f ON f.id = sf.file_id
        LEFT JOIN tblProjectVersions pv
            ON pv.file_id = f.id AND pv.version_number = 1
        WHERE sf.submission_id = %s
        ORDER BY f.file_name, sf.id
        """,
        (submission_id,),
    )
    return cursor.fetchall()


def submission_file_repo(cursor, submission_id, submission_file_id):
    cursor.execute(
        """
        SELECT
            sf.id AS submission_file_id,
            f.file_name,
            f.file_type,
            f.current_path AS file_path,
            p.id AS project_id,
            p.student_id
        FROM tblSubmissionFiles sf
        JOIN tblProjectFiles f ON f.id = sf.file_id
        JOIN tblProjects p ON p.id = f.project_id
        WHERE sf.submission_id = %s AND sf.id = %s
        LIMIT 1
        """,
        (submission_id, submission_file_id),
    )
    return cursor.fetchone()
