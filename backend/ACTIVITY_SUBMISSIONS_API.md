# Activity submissions API

Run the single [DATABASE.sql](../../DATABASE.sql) schema against the CLMS
database. Submissions use only the existing `tblSubmissions`,
`tblSubmissionFiles`, `tblProjectFiles`, and `tblProjectVersions` tables.

All endpoints require a bearer access token. Students can access only their
own submissions and must be enrolled in the class. Instructors can access
submissions for their activities; Admins can access all submissions.

## Submit or resubmit

Students first upload files to one of their active projects using the
project-files API. They may revise a file through its project-file versions
endpoint, then submit to capture the current file contents.

`POST /activities/{activity_id}/submissions`

```json
{
  "project_id": 7,
  "file_ids": [21, 22]
}
```

Send 1–20 unique active file IDs, all belonging to the supplied project and
authenticated student. A first submission returns `201`; a resubmission
returns `200`. The response includes the submission ID, status, submission
time, and a `submission_file_id` for each saved file.

Only Published activities accept submissions. Submissions after the due date
are recorded as `Late`. `Accepted` submissions cannot be changed. Any other
current submission can be resubmitted while the activity is Published; the
same submission row is updated and its current file associations are replaced.

The current submission's files are copied into archived project-file records
and their bytes are preserved in private storage. The existing
`tblSubmissionFiles` associations point to those immutable copies, so later
workspace edits, renames, restores, and deletes do not change the current
submitted work. The supplied schema has one submission row per activity and
student; a resubmission replaces that row's current file associations rather
than keeping submission-round history.

## List submissions and files

- `GET /activities/{activity_id}/submissions`: Instructors/Admins get activity
  submissions; Students get their own submission.
- `GET /submissions/{submission_id}/files`: list the current submitted file
  snapshots. Available to the owner, activity Instructor, or Admin.

## Instructor review

`PUT /submissions/{submission_id}/review`

Only the activity's Instructor or an Admin can review. Send a submission
status and optional remarks:

```json
{
  "status": "Returned",
  "remarks": "Please include the missing diagram."
}
```

Statuses are `Returned`, `Accepted`, and `Rejected`. Review state and remarks
are stored on `tblSubmissions` and recorded in the audit history.

## Download a submitted file

`GET /submissions/{submission_id}/files/{submission_file_id}`
returns that exact submitted file as a private attachment. Access follows the
same owner/Instructor/Admin rules.
