from backend.utils.folder_errors import FolderError

def list_projects_in_folder_repo(
    cursor, student_id, folder_id, limit, offset
):
    cursor.execute(
        """
        SELECT
            id,
            student_id,
            folder_id,
            project_name,
            description,
            created_at,
            updated_at,
            deleted_at,
            status
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
        SELECT
            id
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
        SELECT
            id,
            student_id,
            folder_id,
            project_name,
            description,
            created_at,
            updated_at,
            deleted_at,
            status
        FROM tblprojects
        WHERE id = %s
          AND student_id = %s
          AND folder_id = %s
        """,
        (project_id, student_id, folder_id),
    )

    return cursor.fetchone()

def get_owned_project_repo(cursor, student_id, folder_id, project_id):
    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name, description,
               created_at, updated_at, deleted_at, status
        FROM tblProjects
        WHERE id = %s AND student_id = %s AND folder_id = %s
          AND status = 'Active' AND deleted_at IS NULL
        LIMIT 1 FOR UPDATE
        """,
        (project_id, student_id, folder_id),
    )
    return cursor.fetchone()

def update_project_repo(
    cursor, student_id, folder_id, project_id,
    project_name, description, update_description,
):
    if update_description:
        cursor.execute(
            """
            UPDATE tblProjects
            SET project_name = %s, description = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND student_id = %s AND folder_id = %s
              AND status = 'Active' AND deleted_at IS NULL
            """,
            (project_name, description, project_id, student_id, folder_id),
        )
    else:
        cursor.execute(
            """
            UPDATE tblProjects
            SET project_name = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND student_id = %s AND folder_id = %s
              AND status = 'Active' AND deleted_at IS NULL
            """,
            (project_name, project_id, student_id, folder_id),
        )

    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name, description,
               created_at, updated_at, deleted_at, status
        FROM tblProjects
        WHERE id = %s AND student_id = %s AND folder_id = %s
        """,
        (project_id, student_id, folder_id),
    )
    return cursor.fetchone()

def active_project_name_exists_excluding_repo(
    cursor, student_id, folder_id, project_name, excluded_project_id
):
    cursor.execute(
        """
        SELECT id
        FROM tblProjects
        WHERE student_id = %s AND folder_id = %s
          AND project_name = %s AND id <> %s
          AND status = 'Active' AND deleted_at IS NULL
        LIMIT 1
        """,
        (student_id, folder_id, project_name, excluded_project_id),
    )
    return cursor.fetchone() is not None

def soft_delete_project_repo(
    cursor, student_id, folder_id, project_id, deleted_at
):
    cursor.execute(
        """
        UPDATE tblProjects
        SET status = 'Deleted', deleted_at = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND student_id = %s AND folder_id = %s
          AND status = 'Active' AND deleted_at IS NULL
        """,
        (deleted_at, project_id, student_id, folder_id),
    )
    if cursor.rowcount != 1:
        raise FolderError("Project not found or already deleted.", 404)

    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name, description,
               created_at, updated_at, deleted_at, status
        FROM tblProjects
        WHERE id = %s AND student_id = %s AND folder_id = %s
        """,
        (project_id, student_id, folder_id),
    )
    return cursor.fetchone()

def get_deleted_project_repo(cursor, student_id, folder_id, project_id):
    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name, description,
               created_at, updated_at, deleted_at, status
        FROM tblProjects
        WHERE id = %s AND student_id = %s AND folder_id = %s
          AND status = 'Deleted' AND deleted_at IS NOT NULL
        LIMIT 1 FOR UPDATE
        """,
        (project_id, student_id, folder_id),
    )
    return cursor.fetchone()

def restore_project_repo(cursor, student_id, folder_id, project_id):
    cursor.execute(
        """
        UPDATE tblProjects
        SET status = 'Active', deleted_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND student_id = %s AND folder_id = %s
          AND status = 'Deleted' AND deleted_at IS NOT NULL
        """,
        (project_id, student_id, folder_id),
    )
    if cursor.rowcount != 1:
        raise FolderError("Deleted project could not be restored.", 409)

    cursor.execute(
        """
        SELECT id, student_id, folder_id, project_name, description,
               created_at, updated_at, deleted_at, status
        FROM tblProjects
        WHERE id = %s AND student_id = %s AND folder_id = %s
        """,
        (project_id, student_id, folder_id),
    )
    return cursor.fetchone()