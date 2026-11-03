# Class management and enrollment API

All endpoints require a bearer access token. Classes and memberships use
`tblClasses` and `tblClassMembers` from [DATABASE.sql](../../DATABASE.sql).

| Method | Endpoint | Access |
|---|---|---|
| GET | `/classes` | Admin, Instructor, Student; results scoped to caller |
| POST | `/classes` | Instructor |
| GET | `/classes/{class_id}` | Admin, owning Instructor, enrolled Student |
| PUT | `/classes/{class_id}` | Admin or owning Instructor |
| DELETE | `/classes/{class_id}` | Admin or owning Instructor; archives |
| GET | `/classes/{class_id}/members` | Admin or owning Instructor |
| POST | `/classes/{class_id}/members` | Admin or owning Instructor |
| PUT | `/classes/{class_id}/members/{student_id}` | Admin or owning Instructor |
| POST | `/classes/join` | Student |

Create a class:

```json
{
  "class_name": "Programming 1",
  "school_year": "2026-2027",
  "semester": "First Semester",
  "description": "Optional class description"
}
```

`semester` must be `First Semester`, `Second Semester`, or `Summer`. The
response includes a generated `class_code` for student enrollment.

Instructor/Admin enrollment uses `{"student_id": 12}`. Membership status can be
`Enrolled`, `Dropped`, or `Completed`. A dropped student can be re-enrolled; a
completed membership cannot be reopened.

Students join using `{"class_code": "ABCDEFG234"}`.

Class creation, updates, archiving, student enrollment, and joining are written
to the shared audit log.
