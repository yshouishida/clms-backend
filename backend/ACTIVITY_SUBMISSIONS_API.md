# Activity submissions API

Run `database/submission_versions.sql` against the CLMS database after the base schema. It adds immutable submission-round snapshots that point to exact `tblProjectVersions` rows; the existing `tblSubmissions` and `tblSubmissionFiles` tables remain the current-submission records.

All endpoints require a Bearer JWT. Students can access only their own submissions and must be enrolled in the class. Instructors can access submissions for their own activities; Admins can access all submissions.

## Submit or resubmit

Students first upload files to one of their active projects using the project-files API. They may revise a file through its existing project-file versions endpoint, then submit again to capture that revision as a new submission round.

`POST /activities/{activity_id}/submissions`

```json
{
  "project_id": 7,
  "file_ids": [21, 22]
}
```

Send 1–20 unique active file IDs, all belonging to the supplied project and authenticated student. A first submission returns `201`; a resubmission returns `200`. The response includes `submission_id`, `version_number`, status, submission time, and the pinned `project_version_id` for each file. Each submission round retains its own file list and exact project-file versions.

Only Published activities accept submissions. A submission after the due date is accepted with status `Late`. Accepted submissions cannot be changed; otherwise students can resubmit while the activity remains Published.

## View submissions and versions

- `GET /activities/{activity_id}/submissions`: Instructor/Admin receives submissions for the activity; Student receives their own submission, if any.
- `GET /submissions/{submission_id}/versions`: list immutable submission rounds and their file snapshots. Available to the owner, activity instructor, or Admin.

## Download a submitted file

`GET /submissions/{submission_id}/versions/{version_number}/files/{project_version_id}` returns that exact submitted file as a private attachment. Access follows the same owner/instructor/Admin rules. The version ID is provided by the submission or version-history response.
