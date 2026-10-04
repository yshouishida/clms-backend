import unicodedata

from backend.utils.folder_errors import FolderError

MAX_FOLDER_DEPTH = 32

ROOT_KEYS = {
    "project": "PROJECT",
    "activities": "ACTIVITIES",
}

FOLDER_COLUMNS = """
    id, student_id, parent_folder_id, folder_name,
    created_at, deleted_at, status
"""


def name_key(name):
    return unicodedata.normalize("NFC", name).strip().casefold()


def root_key(row):
    if row["parent_folder_id"] is None:
        return ROOT_KEYS.get(name_key(row["folder_name"]))

    return None


def require_active_student_repo(cursor, user_id):
    # Lock the account row while its folder transaction runs.
    cursor.execute(
        """
        SELECT u.status, r.role_name, s.id AS student_id
        FROM tblUsers u
        JOIN tblRoles r ON r.id = u.role_id
        LEFT JOIN tblStudents s ON s.user_id = u.id
        WHERE u.id = %s
        LIMIT 1 FOR UPDATE
        """,
        (user_id,),
    )

    user = cursor.fetchone()

    if user is None or user["status"] != "Active":
        raise FolderError("An active account is required.", 403)

    if (
        user["student_id"] is None
        or user["role_name"].casefold() != "student"
    ):
        raise FolderError("An active student account is required.", 403)

    return user["student_id"]


def list_roots_repo(cursor, student_id):
    # Include inactive roots so initialization does not recreate them.
    cursor.execute(
        f"""
        SELECT {FOLDER_COLUMNS}
        FROM tblFolders
        WHERE student_id = %s
          AND parent_folder_id IS NULL
        ORDER BY id
        """,
        (student_id,),
    )

    return cursor.fetchall()


def insert_root_repo(cursor, student_id, name):
    cursor.execute(
        """
        INSERT INTO tblFolders (
            student_id,
            parent_folder_id,
            folder_name,
            created_at,
            status
        )
        VALUES (%s, NULL, %s, CURRENT_TIMESTAMP, 'Active')
        """,
        (student_id, name),
    )


def get_active_folder_repo(cursor, student_id, folder_id):
    visited = set()
    target = None
    current_id = folder_id

    # Check the folder and every parent up to its permanent root.
    while current_id is not None:
        if current_id in visited or len(visited) >= MAX_FOLDER_DEPTH:
            raise FolderError("Folder hierarchy is unavailable.", 404)

        visited.add(current_id)

        cursor.execute(
            f"""
            SELECT {FOLDER_COLUMNS}
            FROM tblFolders
            WHERE id = %s
              AND student_id = %s
              AND status = 'Active'
              AND deleted_at IS NULL
            """,
            (current_id, student_id),
        )

        row = cursor.fetchone()

        if row is None:
            raise FolderError("Folder not found.", 404)

        if target is None:
            target = row

        if row["parent_folder_id"] is None and root_key(row) is None:
            raise FolderError("Folder hierarchy is unavailable.", 404)

        current_id = row["parent_folder_id"]

    return target, len(visited)


def list_children_repo(cursor, student_id, folder_id, limit, offset):
    cursor.execute(
        f"""
        SELECT {FOLDER_COLUMNS}
        FROM tblFolders
        WHERE student_id = %s
          AND parent_folder_id = %s
          AND status = 'Active'
          AND deleted_at IS NULL
        ORDER BY folder_name, id
        LIMIT %s OFFSET %s
        """,
        (student_id, folder_id, limit + 1, offset),
    )

    return cursor.fetchall()


def sibling_name_exists_repo(
    cursor,
    student_id,
    parent_id,
    normalized_name,
):
    # Retained deleted/archived names remain reserved for now.
    cursor.execute(
        """
        SELECT folder_name
        FROM tblFolders
        WHERE student_id = %s
          AND parent_folder_id = %s
        """,
        (student_id, parent_id),
    )

    return any(
        name_key(row["folder_name"]) == normalized_name
        for row in cursor.fetchall()
    )


def insert_folder_repo(cursor, student_id, parent_id, name):
    cursor.execute(
        """
        INSERT INTO tblFolders (
            student_id,
            parent_folder_id,
            folder_name,
            created_at,
            status
        )
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 'Active')
        """,
        (student_id, parent_id, name),
    )

    return cursor.lastrowid