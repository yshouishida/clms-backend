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
        SELECT id, student_id, status, deleted_at
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


def latest_project_version_repo(cursor, file_id):
    cursor.execute(
        """
        SELECT id, version_number, file_path, file_size
        FROM tblProjectVersions
        WHERE file_id = %s
        ORDER BY version_number DESC, id DESC
        LIMIT 1
        FOR UPDATE
        """,
        (file_id,),
    )
    return cursor.fetchone()


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


def create_submission_version_repo(cursor, submission_id, version_number, status):
    cursor.execute(
        """
        INSERT INTO tblSubmissionVersions
            (submission_id, version_number, submitted_at, status)
        VALUES (%s, %s, UTC_TIMESTAMP(), %s)
        """,
        (submission_id, version_number, status),
    )
    return cursor.lastrowid


def insert_submission_version_file_repo(cursor, submission_version_id, project_version_id, file):
    cursor.execute(
        """
        INSERT INTO tblSubmissionVersionFiles
            (submission_version_id, project_version_id, file_name, file_type, file_size)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (submission_version_id, project_version_id, file["file_name"],
         file["file_type"], file["file_size"]),
    )


def replace_submission_files_repo(cursor, submission_id, file_ids):
    cursor.execute(
        "DELETE FROM tblSubmissionFiles WHERE submission_id = %s",
        (submission_id,),
    )
    for file_id in file_ids:
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
            u.last_name,
            (SELECT MAX(sv.version_number)
             FROM tblSubmissionVersions sv
             WHERE sv.submission_id = s.id) AS latest_version
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


def list_submission_versions_repo(cursor, submission_id):
    cursor.execute(
        """
        SELECT id, submission_id, version_number, submitted_at, status
        FROM tblSubmissionVersions
        WHERE submission_id = %s
        ORDER BY version_number DESC
        """,
        (submission_id,),
    )
    return cursor.fetchall()


def list_submission_version_files_repo(cursor, submission_version_id):
    cursor.execute(
        """
        SELECT
            svf.project_version_id,
            svf.file_name,
            svf.file_type,
            svf.file_size,
            pv.version_number AS file_version
        FROM tblSubmissionVersionFiles svf
        JOIN tblProjectVersions pv ON pv.id = svf.project_version_id
        WHERE svf.submission_version_id = %s
        ORDER BY svf.file_name, svf.project_version_id
        """,
        (submission_version_id,),
    )
    return cursor.fetchall()


def submission_file_repo(cursor, submission_id, version_number, project_version_id):
    cursor.execute(
        """
        SELECT
            svf.file_name,
            svf.file_type,
            pv.file_path,
            p.id AS project_id,
            p.student_id
        FROM tblSubmissionVersionFiles svf
        JOIN tblSubmissionVersions sv ON sv.id = svf.submission_version_id
        JOIN tblSubmissions s ON s.id = sv.submission_id
        JOIN tblProjectVersions pv ON pv.id = svf.project_version_id
        JOIN tblProjectFiles pf ON pf.id = pv.file_id
        JOIN tblProjects p ON p.id = pf.project_id
        WHERE s.id = %s AND sv.version_number = %s
          AND svf.project_version_id = %s
        LIMIT 1
        """,
        (submission_id, version_number, project_version_id),
    )
    return cursor.fetchone()
