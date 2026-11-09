from backend.utils.folder_errors import FolderError

def get_active_project_repo(
    cursor, student_id, folder_id, project_id
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
        SELECT
            id,
            project_id,
            folder_id,
            file_name,
            file_type,
            file_size,
            created_at,
            updated_at,
            status
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
        SELECT
            id
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
        SELECT
            id,
            project_id,
            folder_id,
            file_name,
            file_type,
            file_size,
            created_at,
            updated_at,
            status
        FROM tblprojectfiles
        WHERE id = %s
          AND project_id = %s
        """,
        (file_id, project_id),
    )

    return cursor.fetchone()

def get_owned_project_file_repo(
    cursor, student_id, folder_id, project_id, file_id
):
    cursor.execute(
        """
        SELECT f.id, f.project_id, f.folder_id, f.file_name, f.file_type,
               f.file_size, f.current_path, f.created_at, f.updated_at,
               f.deleted_at, f.status
        FROM tblProjectFiles f
        JOIN tblProjects p ON p.id = f.project_id
        WHERE f.id = %s AND f.project_id = %s
          AND p.folder_id = %s AND p.student_id = %s
          AND p.status = 'Active' AND p.deleted_at IS NULL
          AND f.status = 'Active' AND f.deleted_at IS NULL
        LIMIT 1 FOR UPDATE
        """,
        (file_id, project_id, folder_id, student_id),
    )
    return cursor.fetchone()

def file_name_exists_excluding_repo(cursor, project_id, file_name, file_id):
    cursor.execute(
        """
        SELECT id
        FROM tblProjectFiles
        WHERE project_id = %s AND file_name = %s
          AND id <> %s AND status = 'Active' AND deleted_at IS NULL
        LIMIT 1
        """,
        (project_id, file_name, file_id),
    )
    return cursor.fetchone() is not None

def rename_project_file_repo(cursor, project_id, file_id, file_name):
    cursor.execute(
        """
        UPDATE tblProjectFiles
        SET file_name = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND project_id = %s
          AND status = 'Active' AND deleted_at IS NULL
        """,
        (file_name, file_id, project_id),
    )
    cursor.execute(
        """
        SELECT id, project_id, folder_id, file_name, file_type, file_size,
               created_at, updated_at, status
        FROM tblProjectFiles
        WHERE id = %s AND project_id = %s
        """,
        (file_id, project_id),
    )
    return cursor.fetchone()

def soft_delete_project_file_repo(cursor, project_id, file_id, deleted_at):
    cursor.execute(
        """
        UPDATE tblProjectFiles
        SET status = 'Deleted', deleted_at = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND project_id = %s
          AND status = 'Active' AND deleted_at IS NULL
        """,
        (deleted_at, file_id, project_id),
    )
    if cursor.rowcount != 1:
        raise FolderError("File not found or already deleted.", 404)
    cursor.execute(
        """
        SELECT id, project_id, folder_id, file_name, file_type, file_size,
               created_at, updated_at, status
        FROM tblProjectFiles
        WHERE id = %s AND project_id = %s
        """,
        (file_id, project_id),
    )
    return cursor.fetchone()

def soft_delete_active_project_files_repo(cursor, project_id, deleted_at):
    cursor.execute(
        """
        UPDATE tblProjectFiles
        SET status = 'Deleted', deleted_at = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE project_id = %s
          AND status = 'Active' AND deleted_at IS NULL
        """,
        (deleted_at, project_id),
    )
    return cursor.rowcount

def restore_project_files_repo(cursor, project_id, project_deleted_at):
    # Only restore files that were active when the project was deleted.
    # Files deleted earlier have a different deleted_at value and stay deleted.
    cursor.execute(
        """
        UPDATE tblProjectFiles
        SET status = 'Active', deleted_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE project_id = %s
          AND status = 'Deleted'
          AND deleted_at = %s
        """,
        (project_id, project_deleted_at),
    )
    return cursor.rowcount

def list_active_project_files_for_snapshot_repo(
    cursor, student_id, folder_id, project_id
):
    cursor.execute(
        """
        SELECT f.id, f.project_id, f.folder_id, f.file_name, f.file_type,
               f.file_size, f.current_path, f.created_at, f.updated_at,
               f.deleted_at, f.status
        FROM tblProjectFiles f
        JOIN tblProjects p ON p.id = f.project_id
        WHERE f.project_id = %s AND p.student_id = %s
          AND p.folder_id = %s AND p.status = 'Active'
          AND p.deleted_at IS NULL
          AND f.status = 'Active' AND f.deleted_at IS NULL
        ORDER BY f.id
        FOR UPDATE
        """,
        (project_id, student_id, folder_id),
    )
    return cursor.fetchall()

def get_project_file_record_for_snapshot_repo(
    cursor, student_id, folder_id, project_id, file_id
):
    cursor.execute(
        """
        SELECT f.id, f.project_id, f.folder_id, f.file_name, f.file_type,
               f.file_size, f.current_path, f.created_at, f.updated_at,
               f.deleted_at, f.status
        FROM tblProjectFiles f
        JOIN tblProjects p ON p.id = f.project_id
        WHERE f.id = %s AND f.project_id = %s
          AND p.folder_id = %s AND p.student_id = %s
        LIMIT 1 FOR UPDATE
        """,
        (file_id, project_id, folder_id, student_id),
    )
    return cursor.fetchone()

def restore_snapshot_file_repo(
    cursor, project_id, file_id, folder_id, file_name, file_type, file_size, current_path
):
    cursor.execute(
        """
        UPDATE tblProjectFiles
        SET folder_id = %s, file_name = %s, file_type = %s, file_size = %s,
            current_path = %s, status = 'Active', deleted_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND project_id = %s
        """,
        (folder_id, file_name, file_type, file_size, current_path, file_id, project_id),
    )
    if cursor.rowcount not in (0, 1):
        raise FolderError("Unexpected file restore result.", 500)
    cursor.execute(
        """
        SELECT id, project_id, folder_id, file_name, file_type, file_size,
               created_at, updated_at, status
        FROM tblProjectFiles WHERE id = %s AND project_id = %s
        """,
        (file_id, project_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise FolderError("Project file no longer exists; recovery is impossible.", 409)
    return row
