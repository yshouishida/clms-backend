def activity_report_repo(cursor, class_id):
    cursor.execute(
        """
        SELECT
            a.id AS activity_id,
            a.class_id,
            a.activity_name,
            a.due_date,
            a.status,
            COUNT(DISTINCT CASE WHEN cm.status = 'Enrolled' THEN cm.student_id END)
                AS enrolled_students,
            COUNT(DISTINCT s.student_id) AS students_submitted,
            COUNT(DISTINCT CASE WHEN s.status = 'Accepted' THEN s.student_id END)
                AS students_accepted
        FROM tblActivities a
        LEFT JOIN tblClassMembers cm ON cm.class_id = a.class_id
        LEFT JOIN tblSubmissions s
            ON s.activity_id = a.id AND s.student_id = cm.student_id
        WHERE a.class_id = %s
        GROUP BY a.id, a.class_id, a.activity_name, a.due_date, a.status
        ORDER BY a.due_date, a.id
        """,
        (class_id,),
    )
    return cursor.fetchall()


def submission_report_repo(cursor, class_id, activity_id=None):
    query = """
        SELECT
            s.id AS submission_id,
            s.activity_id,
            a.activity_name,
            s.student_id,
            st.student_number,
            u.first_name,
            u.last_name,
            s.project_id,
            s.submitted_at,
            s.status,
            s.remarks
        FROM tblSubmissions s
        JOIN tblActivities a ON a.id = s.activity_id
        JOIN tblStudents st ON st.id = s.student_id
        JOIN tblUsers u ON u.id = st.user_id
        WHERE a.class_id = %s
    """
    params = [class_id]
    if activity_id is not None:
        query += " AND s.activity_id = %s"
        params.append(activity_id)
    cursor.execute(query + " ORDER BY s.submitted_at DESC, s.id DESC", params)
    return cursor.fetchall()


def student_progress_report_repo(cursor, class_id, student_id=None):
    query = """
        SELECT
            st.id AS student_id,
            st.student_number,
            u.first_name,
            u.last_name,
            COUNT(DISTINCT a.id) AS activities_total,
            COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN a.id END)
                AS activities_submitted,
            COUNT(DISTINCT CASE WHEN s.status = 'Accepted' THEN a.id END)
                AS activities_accepted,
            COALESCE(ROUND(
                100 * COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN a.id END)
                / NULLIF(COUNT(DISTINCT a.id), 0),
                2
            ), 0) AS completion_percentage,
            MAX(s.submitted_at) AS last_submission_at
        FROM tblClassMembers cm
        JOIN tblStudents st ON st.id = cm.student_id
        JOIN tblUsers u ON u.id = st.user_id
        LEFT JOIN tblActivities a
            ON a.class_id = cm.class_id AND a.status IN ('Published', 'Closed')
        LEFT JOIN tblSubmissions s
            ON s.activity_id = a.id AND s.student_id = st.id
        WHERE cm.class_id = %s AND cm.status = 'Enrolled'
    """
    params = [class_id]
    if student_id is not None:
        query += " AND st.id = %s"
        params.append(student_id)
    query += """
        GROUP BY st.id, st.student_number, u.first_name, u.last_name
        ORDER BY u.last_name, u.first_name, st.id
    """
    cursor.execute(query, params)
    return cursor.fetchall()
