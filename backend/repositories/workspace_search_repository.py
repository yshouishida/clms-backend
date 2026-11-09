def search_workspace_repo(cursor, student_id, query, kind, limit, offset):
    pattern = f"%{query}%"
    statements = []
    params = []

    if kind in ("all", "folder"):
        statements.append(
            """
            SELECT 'folder' AS result_type,
                   f.id AS result_id,
                   f.folder_name AS name,
                   f.parent_folder_id AS parent_id,
                   NULL AS project_id,
                   NULL AS folder_id,
                   NULL AS file_type,
                   f.created_at As updated_at
            FROM tblFolders f
            WHERE f.student_id = %s
              AND f.parent_folder_id IS NOT NULL
              AND f.status = 'Active' AND f.deleted_at IS NULL
              AND f.folder_name LIKE %s
            """
        )
        params.extend((student_id, pattern))

    if kind in ("all", "project"):
        statements.append(
            """
            SELECT 'project' AS result_type,
                   p.id AS result_id,
                   p.project_name AS name,
                   p.folder_id AS parent_id,
                   p.id AS project_id,
                   p.folder_id AS folder_id,
                   NULL AS file_type,
                   p.updated_at AS updated_at
            FROM tblProjects p
            WHERE p.student_id = %s
              AND p.status = 'Active' AND p.deleted_at IS NULL
              AND (p.project_name LIKE %s OR p.description LIKE %s)
            """
        )
        params.extend((student_id, pattern, pattern))

    if kind in ("all", "file"):
        statements.append(
            """
            SELECT 'file' AS result_type,
                   f.id AS result_id,
                   f.file_name AS name,
                   f.project_id AS parent_id,
                   f.project_id AS project_id,
                   f.folder_id AS folder_id,
                   f.file_type AS file_type,
                   f.updated_at AS updated_at
            FROM tblProjectFiles f
            JOIN tblProjects p ON p.id = f.project_id
            WHERE p.student_id = %s
              AND p.status = 'Active' AND p.deleted_at IS NULL
              AND f.status = 'Active' AND f.deleted_at IS NULL
              AND f.file_name LIKE %s
            """
        )
        params.extend((student_id, pattern))

    sql = (
        " UNION ALL ".join(statements)
        + " ORDER BY name ASC, result_type ASC, result_id ASC LIMIT %s OFFSET %s"
    )
    params.extend((limit + 1, offset))
    cursor.execute(sql, tuple(params))
    return cursor.fetchall()