# Student submissions and instructor review

The routes below require a Bearer token. `POST` is for an active Student;
all other routes are for an active Instructor who owns both the activity and
its class. Admin has no access through these routes.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/activities/<activity_id>/submissions` | Submit one project with pinned versions. |
| `GET` | `/activities/<activity_id>/submissions` | List an owning instructor's submissions. |
| `GET` | `/submissions/<submission_id>` | Open one submission and its pinned links. |
| `PATCH` | `/submissions/<submission_id>/review` | Review once. |
| `GET` | `/submissions/<submission_id>/files/<submission_file_id>/content` | Download the pinned bytes as an attachment. |

Submit JSON: `{ "project_id": 7, "version_ids": [11, 12] }`. The IDs must be
distinct, from distinct active files in the student's selected active project,
and contain 1 to 100 entries. The Student identity comes from the token. The
student must be enrolled in an active class with a Published activity. The
response includes the submission ID, status, UTC `submitted_at`, and each
link's `submission_file_id`, `file_id`, and `version_id`. The parent and links
are saved in one transaction.

The activity's `due_date` is interpreted as UTC. A submission at the deadline
is `Submitted`; one after it is accepted as `Late`. The server saves the same
UTC timestamp used for that comparison. An identical retry returns HTTP 200
and the existing row. A different second attempt returns HTTP 409. A
`Returned` review does not permit a new attempt in this release.

Review JSON: `{ "status": "Accepted", "remarks": "Good work" }`. Status may
be `Returned`, `Accepted`, or `Rejected`. Remarks are optional text or null.
Only a `Submitted` or `Late` row can be reviewed. A later review request
returns HTTP 409; reviewing never changes pinned file links.

The download route first checks the instructor's activity and class ownership,
then checks that the link belongs to the requested submission. It passes the
stored `version_id` to `read_file_version_service(version_id)`. An unresolved
legacy link or missing historical bytes returns HTTP 409. The file response
uses `Cache-Control: private, no-store`.

Deployment requires V04 plus migrations `001_submission_file_version_pin_prepare.sql`
and `002_submission_file_version_pin_enforce.sql`. On an application database,
the DBA must establish every legacy link's original submitted version from
reliable evidence before applying phase 2. Do not infer it from the current
project path or latest version. V04 retains only one submission per student
and activity. A later multiple-attempt policy needs a schema change. V04 also
stores lateness in the review status field, so reviewing changes that field;
durable separate lateness would need a schema change.

Run the isolated MySQL API test from the repository root with the authorized
`CLMS_TEST_DB_USER` account and optional `CLMS_TEST_DB_PASSWORD`,
`CLMS_TEST_DB_HOST`, and `CLMS_TEST_DB_PORT` variables:

```text
python -B -m unittest backend.test_submissions_workflow -v
```

The test creates and drops its own randomly named database and uses temporary
file storage. `OK (skipped=1)` is not a MySQL integration pass.
