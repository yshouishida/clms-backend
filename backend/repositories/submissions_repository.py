"""Submission queries. All operations use the caller's transaction."""


def activity_for_student_repo(cursor, activity_id, student_id):
    cursor.execute(
        """
        SELECT a.id, a.class_id, a.instructor_id, a.due_date,
               a.status, c.status AS class_status,
               c.instructor_id AS class_instructor_id,
               cm.status AS membership_status
        FROM tblActivities a
        JOIN tblClasses c ON c.id = a.class_id
        JOIN tblClassMembers cm ON cm.class_id = c.id
        WHERE a.id = %s AND cm.student_id = %s
        FOR UPDATE
        """,
        (activity_id, student_id),
    )
    return cursor.fetchone()


def owned_project_repo(cursor, project_id, student_id):
    cursor.execute(
        """
        SELECT id FROM tblProjects
        WHERE id = %s AND student_id = %s
          AND status = 'Active' AND deleted_at IS NULL
        FOR UPDATE
        """,
        (project_id, student_id),
    )
    return cursor.fetchone()


def owned_versions_repo(cursor, version_ids, project_id, student_id):
    placeholders = ", ".join(["%s"] * len(version_ids))
    cursor.execute(
        f"""
        SELECT v.id AS version_id, v.file_id
        FROM tblProjectVersions v
        JOIN tblProjectFiles f ON f.id = v.file_id
        JOIN tblProjects p ON p.id = f.project_id
        WHERE v.id IN ({placeholders})
          AND p.id = %s AND p.student_id = %s
          AND p.status = 'Active' AND p.deleted_at IS NULL
          AND f.status = 'Active' AND f.deleted_at IS NULL
        ORDER BY f.id, v.id
        FOR UPDATE
        """,
        (*version_ids, project_id, student_id),
    )
    return cursor.fetchall()


def existing_submission_repo(cursor, activity_id, student_id, lock=False):
    cursor.execute(
        """
        SELECT id, activity_id, student_id, project_id, submitted_at,
               status, remarks
        FROM tblSubmissions
        WHERE activity_id = %s AND student_id = %s
        """ + (" FOR UPDATE" if lock else ""),
        (activity_id, student_id),
    )
    return cursor.fetchone()


def insert_submission_repo(cursor, activity_id, student_id, project_id, submitted_at, status):
    cursor.execute(
        """
        INSERT INTO tblSubmissions
            (activity_id, student_id, project_id, submitted_at, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (activity_id, student_id, project_id, submitted_at, status),
    )
    return cursor.lastrowid


def insert_submission_file_repo(cursor, submission_id, file_id, version_id):
    cursor.execute(
        """
        INSERT INTO tblSubmissionFiles (submission_id, file_id, version_id)
        VALUES (%s, %s, %s)
        """,
        (submission_id, file_id, version_id),
    )


def submission_files_repo(cursor, submission_id):
    cursor.execute(
        """
        SELECT sf.id AS submission_file_id, sf.file_id, sf.version_id,
               f.file_name, v.version_number, v.file_size
        FROM tblSubmissionFiles sf
        JOIN tblProjectFiles f ON f.id = sf.file_id
        LEFT JOIN tblProjectVersions v
            ON v.id = sf.version_id AND v.file_id = sf.file_id
        WHERE sf.submission_id = %s
        ORDER BY sf.id
        """,
        (submission_id,),
    )
    return cursor.fetchall()


def instructor_activity_repo(cursor, activity_id, instructor_id):
    cursor.execute(
        """
        SELECT a.id FROM tblActivities a
        JOIN tblClasses c ON c.id = a.class_id
        WHERE a.id = %s AND a.instructor_id = %s
          AND c.instructor_id = %s
        """,
        (activity_id, instructor_id, instructor_id),
    )
    return cursor.fetchone()


def instructor_submission_repo(cursor, submission_id, instructor_id, lock=False):
    cursor.execute(
        """
        SELECT s.id, s.activity_id, s.student_id, s.project_id,
               s.submitted_at, s.status, s.remarks,
               a.due_date, a.class_id
        FROM tblSubmissions s
        JOIN tblActivities a ON a.id = s.activity_id
        JOIN tblClasses c ON c.id = a.class_id
        WHERE s.id = %s AND a.instructor_id = %s
          AND c.instructor_id = %s
        """ + (" FOR UPDATE" if lock else ""),
        (submission_id, instructor_id, instructor_id),
    )
    return cursor.fetchone()


def instructor_submissions_repo(cursor, activity_id):
    cursor.execute(
        """
        SELECT id, activity_id, student_id, project_id,
               submitted_at, status, remarks
        FROM tblSubmissions
        WHERE activity_id = %s
        ORDER BY submitted_at DESC, id DESC
        """,
        (activity_id,),
    )
    return cursor.fetchall()


def submission_file_repo(cursor, submission_id, submission_file_id):
    cursor.execute(
        """
        SELECT id, submission_id, file_id, version_id
        FROM tblSubmissionFiles
        WHERE id = %s AND submission_id = %s
        """,
        (submission_file_id, submission_id),
    )
    return cursor.fetchone()


def update_review_repo(cursor, submission_id, status, remarks):
    cursor.execute(
        """
        UPDATE tblSubmissions
        SET status = %s, remarks = %s
        WHERE id = %s
        """,
        (status, remarks, submission_id),
    )
