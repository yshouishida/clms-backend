def insert_issue_repo(
    cursor, workstation_id, reporter_user_id, session_id, fields
):
    cursor.execute(
        """
        INSERT INTO tblIssueReports
            (reported_by, workstation_id, session_id, issue_type, title,
             description, priority, status, reported_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', UTC_TIMESTAMP())
        """,
        (
            reporter_user_id,
            workstation_id,
            session_id,
            fields["issue_type"],
            fields["title"],
            fields["description"],
            fields["priority"],
        ),
    )
    return cursor.lastrowid


def issue_repo(cursor, issue_id, lock=False):
    cursor.execute(
        """
        SELECT
            i.id,
            i.workstation_id,
            i.reported_by,
            i.session_id,
            i.issue_type,
            i.title,
            i.description,
            i.priority,
            i.status,
            i.resolution_details,
            i.reported_at,
            i.resolved_at,
            i.resolved_by,
            reporter.first_name AS reporter_first_name,
            reporter.last_name AS reporter_last_name,
            resolver.first_name AS resolver_first_name,
            resolver.last_name AS resolver_last_name,
            w.pc_name
        FROM tblIssueReports i
        JOIN tblUsers reporter ON reporter.id = i.reported_by
        LEFT JOIN tblUsers resolver ON resolver.id = i.resolved_by
        JOIN tblWorkstations w ON w.id = i.workstation_id
        WHERE i.id = %s
        """ + (" FOR UPDATE" if lock else ""),
        (issue_id,),
    )
    return cursor.fetchone()


def session_workstation_repo(cursor, session_id, workstation_id):
    cursor.execute(
        """
        SELECT id, student_id FROM tblLaboratorySessions
        WHERE id = %s AND workstation_id = %s
        """,
        (session_id, workstation_id),
    )
    return cursor.fetchone()


def update_issue_repo(
    cursor, issue_id, status, resolution_details, resolved_by
):
    cursor.execute(
        """
        UPDATE tblIssueReports
        SET status = %s,
            resolution_details = %s,
            resolved_by = %s,
            resolved_at = CASE
                WHEN %s = 'Resolved' THEN COALESCE(resolved_at, UTC_TIMESTAMP())
                WHEN %s = 'Closed' THEN resolved_at
                ELSE NULL
            END
        WHERE id = %s
        """,
        (status, resolution_details, resolved_by, status, status, issue_id),
    )


def list_issues_repo(
    cursor, limit, offset, user_id=None, workstation_id=None, status=None
):
    query = """
        SELECT
            i.id,
            i.workstation_id,
            i.reported_by,
            i.session_id,
            i.issue_type,
            i.title,
            i.description,
            i.priority,
            i.status,
            i.resolution_details,
            i.reported_at,
            i.resolved_at,
            i.resolved_by,
            reporter.first_name AS reporter_first_name,
            reporter.last_name AS reporter_last_name,
            resolver.first_name AS resolver_first_name,
            resolver.last_name AS resolver_last_name,
            w.pc_name
        FROM tblIssueReports i
        JOIN tblUsers reporter ON reporter.id = i.reported_by
        LEFT JOIN tblUsers resolver ON resolver.id = i.resolved_by
        JOIN tblWorkstations w ON w.id = i.workstation_id
        WHERE 1 = 1
    """
    params = []
    for column, value in (
        ("i.reported_by", user_id),
        ("i.workstation_id", workstation_id),
        ("i.status", status),
    ):
        if value is not None:
            query += f" AND {column} = %s"
            params.append(value)
    query += " ORDER BY i.reported_at DESC, i.id DESC LIMIT %s OFFSET %s"
    cursor.execute(query, (*params, limit, offset))
    return cursor.fetchall()
