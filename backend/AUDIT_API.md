# Audit records API

All modules should write important changes using the shared helper
`backend.utils.audit.record_audit_event(cursor, user_id, action, entity_name,
record_id=None, description=None, ip_address=None)`. Pass the current
transaction cursor so audit records commit or roll back with the action.

The helper writes to `tblAuditLogs` from
[DATABASE.sql](../../DATABASE.sql). Current integrations include
classes/enrollment, activities, submissions/reviews, issues, announcements,
and project file/version changes.

## Retrieve audit history

`GET /audit-logs` is Admin-only. Optional filters:

- `limit` (1–1000, default 100)
- `offset` (nonnegative, default 0)
- `user_id`
- `entity_name`
- `action`

The response includes the event, actor name, entity/record identifiers,
description, IP address, and timestamp.
