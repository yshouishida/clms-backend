




def list_projects_in_folder_repo(
    cursor, student_id, folder_id, limit, offset
):
    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name,
               description, created_at, updated_at,
               deleted_at, status
        FROM tblprojects
        WHERE folder_id = %s
          AND student_id = %s
          AND deleted_at IS NULL
        ORDER BY project_name, id
        LIMIT %s OFFSET %s
        """,
        (folder_id, student_id, limit + 1, offset),
    )

    return cursor.fetchall()

def project_name_exists_repo(
    cursor, student_id, folder_id, project_name
):
    cursor.execute(
        """
        SELECT id
        FROM tblprojects
        WHERE student_id = %s
          AND folder_id = %s
          AND project_name = %s
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (student_id, folder_id, project_name),
    )

    return cursor.fetchone() is not None


def insert_project_repo(
    cursor, student_id, folder_id, project_name, description
):
    cursor.execute(
        """
        INSERT INTO tblprojects (
            student_id,
            folder_id,
            project_name,
            description
        )
        VALUES (%s, %s, %s, %s)
        """,
        (student_id, folder_id, project_name, description),
    )

    project_id = cursor.lastrowid

    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name,
               description, created_at, updated_at,
               deleted_at, status
        FROM tblprojects
        WHERE id = %s
          AND student_id = %s
          AND folder_id = %s
        """,
        (project_id, student_id, folder_id),
    )

    return cursor.fetchone()

