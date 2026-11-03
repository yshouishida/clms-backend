def list_announcements_repo(cursor, class_id, include_archived=False):
    query = """
        SELECT
            a.id,
            a.class_id,
            a.author_id,
            a.title,
            a.content,
            a.posted_at,
            a.status,
            u.first_name AS author_first_name,
            u.last_name AS author_last_name
        FROM tblAnnouncements a
        JOIN tblUsers u ON u.id = a.author_id
        WHERE a.class_id = %s
    """
    if not include_archived:
        query += " AND a.status = 'Published'"
    cursor.execute(query + " ORDER BY a.posted_at DESC, a.id DESC", (class_id,))
    return cursor.fetchall()


def insert_announcement_repo(cursor, class_id, author_id, title, content):
    cursor.execute(
        """
        INSERT INTO tblAnnouncements
            (class_id, author_id, title, content, posted_at, status)
        VALUES (%s, %s, %s, %s, UTC_TIMESTAMP(), 'Published')
        """,
        (class_id, author_id, title, content),
    )
    return cursor.lastrowid


def announcement_class_repo(cursor, announcement_id, lock=False):
    cursor.execute(
        """
        SELECT id, class_id, author_id, title, content, posted_at, status
        FROM tblAnnouncements
        WHERE id = %s
        """ + (" FOR UPDATE" if lock else ""),
        (announcement_id,),
    )
    return cursor.fetchone()


def announcement_detail_repo(cursor, announcement_id):
    cursor.execute(
        """
        SELECT
            a.id,
            a.class_id,
            a.author_id,
            a.title,
            a.content,
            a.posted_at,
            a.status,
            u.first_name AS author_first_name,
            u.last_name AS author_last_name
        FROM tblAnnouncements a
        JOIN tblUsers u ON u.id = a.author_id
        WHERE a.id = %s
        """,
        (announcement_id,),
    )
    return cursor.fetchone()


def update_announcement_repo(cursor, announcement_id, title, content, status):
    cursor.execute(
        """
        UPDATE tblAnnouncements
        SET title = %s, content = %s, status = %s
        WHERE id = %s
        """,
        (title, content, status, announcement_id),
    )
