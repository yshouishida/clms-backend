# Teaching activities API

All endpoints require a bearer access token. Activity data is stored in
`tblActivities` in [DATABASE.sql](../../DATABASE.sql).

| Method | Endpoint | Access |
|---|---|---|
| GET | `/classes/{class_id}/activities` | Admin, owning Instructor, enrolled Student |
| POST | `/classes/{class_id}/activities` | Owning Instructor |
| GET | `/activities/{activity_id}` | Admin, owning Instructor, enrolled Student |
| PUT | `/activities/{activity_id}` | Admin or owning Instructor |
| PUT | `/activities/{activity_id}/status` | Admin or owning Instructor |
| DELETE | `/activities/{activity_id}` | Admin or owning Instructor; archives |

Create/update requires exactly `activity_name`, `instructions`, and `due_date`.
The due date is an ISO-8601 datetime. New activities start as `Draft`.

Publish or change an activity status with `{"status": "Published"}`. Allowed
transitions are Draft → Published/Archived, Published → Closed/Archived, and
Closed → Archived. Only Published activities accept student submissions.
Submissions after the deadline are marked `Late`.

Activity creation, edits, and status changes use the shared audit helper.
