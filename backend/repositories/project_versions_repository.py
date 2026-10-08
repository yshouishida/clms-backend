"""SQL for file versions. All calls use the caller's transaction."""
VERSION_COLUMNS = """
    id, file_id, version_number, file_size, created_by, created_at
"""


def get_owned_file_repo(cursor, student_id, folder_id, project_id, file_id):
    # Lock the file while assigning the next version and changing current_path.
    # The file's folder_id is not used here: it may be NULL or a future subfolder.
    cursor.execute(
        """
        SELECT f.id, f.project_id, f.folder_id, f.file_name, f.file_type,
               f.file_size, f.current_path, f.created_at, f.updated_at,
               f.deleted_at, f.status
        FROM tblprojectfiles f
        JOIN tblprojects p ON p.id = f.project_id
        WHERE f.id = %s
          AND f.project_id = %s
          AND p.folder_id = %s
          AND p.student_id = %s
          AND p.status = 'Active'
          AND p.deleted_at IS NULL
          AND f.status = 'Active'
          AND f.deleted_at IS NULL
        LIMIT 1 FOR UPDATE
        """,
        (file_id, project_id, folder_id, student_id),
    )
    return cursor.fetchone()


def latest_version_number_repo(cursor, file_id):
    cursor.execute(
        """
        SELECT COALESCE(MAX(version_number), 0) AS latest_number
        FROM tblprojectversions
        WHERE file_id = %s
        """,
        (file_id,),
    )
    return cursor.fetchone()["latest_number"]


def insert_version_repo(
    cursor, file_id, version_number, file_path, file_size, user_id
):
    cursor.execute(
        """
        INSERT INTO tblprojectversions (
            file_id, version_number, file_path,
            file_size, created_by, created_at
        )
        VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP())
        """,
        (file_id, version_number, file_path, file_size, user_id),
    )
    version_id = cursor.lastrowid
    cursor.execute(
        f"""
        SELECT {VERSION_COLUMNS}
        FROM tblprojectversions
        WHERE id = %s AND file_id = %s
        """,
        (version_id, file_id),
    )
    return cursor.fetchone()


def update_current_file_repo(
    cursor, file_id, file_path, file_size, file_type
):
    cursor.execute(
        """
        UPDATE tblprojectfiles
        SET current_path = %s,
            file_size = %s,
            file_type = %s
        WHERE id = %s
        """,
        (file_path, file_size, file_type, file_id),
    )


def list_versions_repo(cursor, file_id, limit, offset):
    cursor.execute(
        f"""
        SELECT {VERSION_COLUMNS}
        FROM tblprojectversions
        WHERE file_id = %s
        ORDER BY version_number DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        (file_id, limit + 1, offset),
    )
    return cursor.fetchall()
