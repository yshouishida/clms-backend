"""SQL for project-file versions and post-failure storage checks."""

from backend.database.connection import get_connection


VERSION_COLUMNS = """
    id,
    file_id,
    version_number,
    file_size,
    created_by,
    created_at
"""


def get_owned_file_repo(cursor, student_id, folder_id, project_id, file_id):
    # Lock the file while assigning the next version and changing current_path.
    # The file's folder_id may be NULL or a future subfolder.
    cursor.execute(
        """
        SELECT
            f.id,
            f.project_id,
            f.folder_id,
            f.file_name,
            f.file_type,
            f.file_size,
            f.current_path,
            f.created_at,
            f.updated_at,
            f.deleted_at,
            f.status
        FROM tblProjectFiles f
        JOIN tblProjects p ON p.id = f.project_id
        WHERE f.id = %s
          AND f.project_id = %s
          AND p.folder_id = %s
          AND p.student_id = %s
          AND p.status = 'Active'
          AND p.deleted_at IS NULL
          AND f.status = 'Active'
          AND f.deleted_at IS NULL
        LIMIT 1
        FOR UPDATE
        """,
        (file_id, project_id, folder_id, student_id),
    )
    return cursor.fetchone()


def latest_version_number_repo(cursor, file_id):
    cursor.execute(
        """
        SELECT COALESCE(MAX(version_number), 0) AS latest_number
        FROM tblProjectVersions
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
        INSERT INTO tblProjectVersions (
            file_id,
            version_number,
            file_path,
            file_size,
            created_by,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP())
        """,
        (file_id, version_number, file_path, file_size, user_id),
    )

    version_id = cursor.lastrowid
    cursor.execute(
        f"""
        SELECT {VERSION_COLUMNS}
        FROM tblProjectVersions
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
        UPDATE tblProjectFiles
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
        FROM tblProjectVersions
        WHERE file_id = %s
        ORDER BY version_number DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        (file_id, limit + 1, offset),
    )
    return cursor.fetchall()


def get_stored_version_repo(cursor, version_id):
    """Return storage metadata for a version, including a deleted file's version."""
    cursor.execute(
        """
        SELECT
            v.id,
            v.file_id,
            v.version_number,
            v.file_path,
            v.file_size,
            f.file_name
        FROM tblProjectVersions v
        JOIN tblProjectFiles f ON f.id = v.file_id
        WHERE v.id = %s
        LIMIT 1
        """,
        (version_id,),
    )
    return cursor.fetchone()


def stored_path_is_referenced_repo(path):
    """Check a fresh connection before removing a file after a failed commit."""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    EXISTS(
                        SELECT 1
                        FROM tblProjectVersions
                        WHERE file_path = %s
                    )
                    OR EXISTS(
                        SELECT 1
                        FROM tblProjectFiles
                        WHERE current_path = %s
                    ) AS referenced
                """,
                (str(path), str(path)),
            )
            return bool(cursor.fetchone()["referenced"])
    finally:
        connection.close()


def get_version_by_number_repo(cursor, file_id, version_number):
    cursor.execute(
        """
        SELECT
            id,
            file_id,
            version_number,
            file_path,
            file_size,
            created_by,
            created_at
        FROM tblProjectVersions
        WHERE file_id = %s AND version_number = %s
        LIMIT 1
        """,
        (file_id, version_number),
    )
    return cursor.fetchone()


def get_version_by_id_repo(cursor, file_id, version_id):
    cursor.execute(
        """
        SELECT
            id,
            file_id,
            version_number,
            file_path,
            file_size,
            created_by,
            created_at
        FROM tblProjectVersions
        WHERE file_id = %s AND id = %s
        LIMIT 1
        """,
        (file_id, version_id),
    )
    return cursor.fetchone()


def get_version_by_path_repo(cursor, file_id, file_path):
    cursor.execute(
        """
        SELECT
            id,
            file_id,
            version_number,
            file_path,
            file_size,
            created_by,
            created_at
        FROM tblProjectVersions
        WHERE file_id = %s AND file_path = %s
        ORDER BY version_number DESC, id DESC
        LIMIT 1
        """,
        (file_id, file_path),
    )
    return cursor.fetchone()