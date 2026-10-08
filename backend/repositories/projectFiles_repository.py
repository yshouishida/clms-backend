def get_active_project_repo(
    cursor, student_id, folder_id, project_id
):
    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name,
               description, created_at, updated_at,
               deleted_at, status
        FROM tblprojects
        WHERE id = %s
          AND student_id = %s
          AND folder_id = %s
          AND status = 'Active'
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (project_id, student_id, folder_id),
    )

    return cursor.fetchone()


def list_project_files_repo(
    cursor, project_id, limit, offset
):
    cursor.execute(
        """
        SELECT id, project_id, folder_id,
               file_name, file_type, file_size,
               created_at, updated_at, status
        FROM tblprojectfiles
        WHERE project_id = %s
          AND status = 'Active'
          AND deleted_at IS NULL
        ORDER BY file_name, id
        LIMIT %s OFFSET %s
        """,
        (project_id, limit + 1, offset),
    )

    return cursor.fetchall()

def file_name_exists_repo(cursor, project_id, file_name):
    cursor.execute(
        """
        SELECT id
        FROM tblprojectfiles
        WHERE project_id = %s
          AND file_name = %s
          AND deleted_at IS NULL
        LIMIT 1
        """,
        (project_id, file_name),
    )

    return cursor.fetchone() is not None


def insert_project_file_repo(
    cursor,
    project_id,
    folder_id,
    file_name,
    file_type,
    file_size,
    current_path,
):
    cursor.execute(
        """
        INSERT INTO tblprojectfiles (
            project_id,
            folder_id,
            file_name,
            file_type,
            file_size,
            current_path
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            project_id,
            folder_id,
            file_name,
            file_type,
            file_size,
            current_path,
        ),
    )

    file_id = cursor.lastrowid

    cursor.execute(
        """
        SELECT id, project_id, folder_id,
               file_name, file_type, file_size,
               created_at, updated_at, status
        FROM tblprojectfiles
        WHERE id = %s
          AND project_id = %s
        """,
        (file_id, project_id),
    )

    return cursor.fetchone()