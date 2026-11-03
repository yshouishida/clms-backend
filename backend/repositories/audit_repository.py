def insert_audit_event_repo(
    cursor, user_id, action, entity_name, record_id, description, ip_address
):
    cursor.execute(
        """
        INSERT INTO tblAuditLogs
            (user_id, action, entity_name, record_id, description, ip_address, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())
        """,
        (user_id, action, entity_name, record_id, description, ip_address),
    )
    return cursor.lastrowid


def list_audit_events_repo(
    cursor, limit, offset, user_id=None, entity_name=None, action=None
):
    query = """
        SELECT
            a.id,
            a.user_id,
            u.first_name,
            u.last_name,
            a.action,
            a.entity_name,
            a.record_id,
            a.description,
            a.ip_address,
            a.created_at
        FROM tblAuditLogs a
        LEFT JOIN tblUsers u ON u.id = a.user_id
        WHERE 1 = 1
    """
    params = []
    for column, value in (
        ("a.user_id", user_id),
        ("a.entity_name", entity_name),
        ("a.action", action),
    ):
        if value is not None:
            query += f" AND {column} = %s"
            params.append(value)
    query += " ORDER BY a.created_at DESC, a.id DESC LIMIT %s OFFSET %s"
    cursor.execute(query, (*params, limit, offset))
    return cursor.fetchall()
