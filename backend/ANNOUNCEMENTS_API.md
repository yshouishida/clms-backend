# Class announcements API

Announcements use `tblAnnouncements` from
[DATABASE.sql](../../DATABASE.sql). All endpoints require a bearer token.

| Method | Endpoint | Access |
|---|---|---|
| GET | `/classes/{class_id}/announcements` | Admin, owning Instructor, enrolled Student |
| POST | `/classes/{class_id}/announcements` | Admin or owning Instructor |
| PUT | `/announcements/{announcement_id}` | Admin or owning Instructor |

Create with `title` and `content`:

```json
{"title": "Lab schedule", "content": "The lab opens at 9 AM."}
```

New announcements are Published. Students see Published announcements only.
Updates require `title`, `content`, and `status` (`Published` or `Archived`).
Creating and updating announcements are audited.
