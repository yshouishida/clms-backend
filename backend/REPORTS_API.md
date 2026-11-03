# Reports API

Report endpoints use GET and require a bearer access token. Class data uses
[DATABASE.sql](../../DATABASE.sql).

| Endpoint | Access | Output |
|---|---|---|
| `GET /reports/activities?class_id={id}` | Admin or owning Instructor | Activity status, enrolled, submitted, and accepted counts |
| `GET /reports/submissions?class_id={id}[&activity_id={id}]` | Admin or owning Instructor | Current submission records, status, and remarks |
| `GET /reports/student-progress?class_id={id}[&student_id={id}]` | Admin, owning Instructor, enrolled Student | Activity/submission counts, completion percentage, last submission |
| `GET /reports/issues` | Admin, Instructor, Student | Issue report list and filters |

Students can only view their own progress. Instructors can view progress and
submissions for their own classes; Admins can view all classes. Issue report
filters are `workstation_id`, `status`, `limit`, and `offset`; students only
see issues they reported.
