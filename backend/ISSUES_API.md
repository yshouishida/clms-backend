# PC issue reporting and resolution API

Issue records use `tblIssueReports` from
[DATABASE.sql](../../DATABASE.sql). All endpoints require a bearer token.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/workstations/{workstation_id}/issues` | Admin, Instructor, Student |
| GET | `/pc-issues` or `/reports/issues` | Admin, Instructor, Student |
| PUT | `/pc-issues/{issue_id}` | Admin or Instructor |

Create an issue report:

```json
{
  "issue_type": "Hardware",
  "title": "PC does not start",
  "description": "Power indicator is on, but the workstation does not boot.",
  "priority": "High",
  "session_id": 42
}
```

`issue_type` is `Hardware`, `Software`, `Network`, `Camera`, `RFID Reader`, or
`Other`. `priority` is optional and defaults to `Medium`; valid values are
`Low`, `Medium`, `High`, and `Critical`. `session_id` is optional and must
belong to the reported workstation. A student can only reference their own
session.

New issues have `Pending` status. List supports optional `workstation_id`,
`status`, `limit`, and `offset`. Students see their own reports; Instructors
and Admins can see all reports.

Update with a status and optional resolution details:

```json
{
  "status": "Resolved",
  "resolution_details": "Replaced the power supply."
}
```

Valid statuses are `Pending`, `Under Review`, `In Progress`, `Resolved`,
`Closed`, and `Rejected`. Status changes follow this flow: Pending can move to
Under Review, In Progress, Resolved, or Rejected; Under Review can move to
In Progress, Resolved, or Rejected; In Progress can move to Resolved or
Rejected; Resolved can move to Closed or back to In Progress; Rejected can
move to Under Review; Closed is final. Resolution details are required when
resolving or rejecting an issue. Resolving records `resolved_by` and
`resolved_at`.
Reporting and status changes create audit records.
