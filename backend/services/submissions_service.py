from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import shutil

from flask import current_app

from backend.database.connection import get_connection
from backend.repositories import activities_repository
from backend.repositories import classes_repository
from backend.repositories import submissions_repository as repo
from backend.utils.audit import record_audit_event
from backend.utils.domain_error import DomainError


class SubmissionError(DomainError):
    pass


@contextmanager
def submission_transaction():
    connection = get_connection()
    try:
        connection.begin()
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def positive_id(value, name):
    if type(value) is not int or value < 1:
        raise SubmissionError(f"{name} must be a positive integer.")
    return value


def _iso(value):
    if value is None:
        return None
    return value.isoformat() + ("Z" if value.tzinfo is None else "")


def _profile_id(cursor, user_id, role):
    if role == "Student":
        profile = classes_repository.get_student_profile_repo(cursor, user_id)
        key = "student_id"
    elif role == "Instructor":
        profile = classes_repository.get_instructor_profile_repo(cursor, user_id)
        key = "instructor_id"
    elif role == "Admin":
        if activities_repository.get_active_admin_repo(cursor, user_id) is None:
            raise SubmissionError("An active Admin account is required.", 403)
        return None
    else:
        raise SubmissionError("Access denied.", 403)
    if profile is None:
        raise SubmissionError("An active account profile is required.", 403)
    return profile[key]


def _authorize_submission(cursor, user_id, role, submission):
    profile_id = _profile_id(cursor, user_id, role)
    if role == "Student" and submission["student_id"] != profile_id:
        raise SubmissionError("Submission not found.", 404)
    if role == "Instructor" and submission["instructor_id"] != profile_id:
        raise SubmissionError("Submission not found.", 404)


def _stored_project_file(student_id, project_id, file_path):
    root = (
        Path(current_app.instance_path) / "project_uploads"
        / str(student_id) / str(project_id)
    ).resolve()
    path = Path(file_path).resolve()
    if path.parent != root or not path.is_file():
        raise SubmissionError("Submitted file is unavailable.", 404)
    return path


def submit_activity_service(user_id, role, activity_id, project_id, file_ids):
    if role != "Student":
        raise SubmissionError("Only students can submit activity files.", 403)
    positive_id(activity_id, "activity_id")
    positive_id(project_id, "project_id")
    if (
        not isinstance(file_ids, list) or not file_ids
        or len(file_ids) > 20
        or any(type(file_id) is not int or file_id < 1 for file_id in file_ids)
        or len(set(file_ids)) != len(file_ids)
    ):
        raise SubmissionError("file_ids must contain 1 to 20 unique positive integers.")

    saved_paths = []
    try:
        with submission_transaction() as cursor:
            activity = repo.lock_activity_repo(cursor, activity_id)
            if activity is None:
                raise SubmissionError("Activity not found.", 404)
            if activity["status"] != "Published":
                raise SubmissionError(
                    "This activity is not accepting submissions.", 409
                )

            membership = repo.student_membership_repo(
                cursor, activity["class_id"], user_id
            )
            if membership is None:
                raise SubmissionError("You are not enrolled in this class.", 403)
            student_id = membership["student_id"]

            project = repo.owned_project_repo(cursor, project_id, student_id)
            if project is None:
                raise SubmissionError("Active project not found.", 404)
            files = repo.owned_project_files_repo(
                cursor, project_id, student_id, file_ids
            )
            if len(files) != len(file_ids):
                raise SubmissionError(
                    "One or more project files are unavailable.", 404
                )

            existing = repo.submission_repo(
                cursor, activity_id, student_id, lock=True
            )
            if existing and existing["status"] == "Accepted":
                raise SubmissionError(
                    "An accepted submission cannot be changed.", 409
                )

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            status = "Late" if now > activity["due_date"] else "Submitted"
            if existing is None:
                submission_id = repo.create_submission_repo(
                    cursor, activity_id, student_id, project_id, status
                )
            else:
                submission_id = existing["id"]
                repo.update_submission_repo(
                    cursor, submission_id, project_id, status
                )

            snapshot_files = []
            for file in files:
                source = _stored_project_file(
                    student_id, project_id, file["current_path"]
                )
                actual_size = source.stat().st_size
                if actual_size != file["file_size"]:
                    raise SubmissionError(
                        f"Project file {file['file_name']} changed; reload and retry.",
                        409,
                    )

                snapshot_path = source.parent / uuid4().hex
                saved_paths.append(snapshot_path)
                shutil.copyfile(source, snapshot_path)
                snapshot_file_id = repo.insert_submission_snapshot_file_repo(
                    cursor,
                    project_id,
                    project["folder_id"],
                    file["file_name"],
                    file["file_type"],
                    actual_size,
                    str(snapshot_path),
                )
                snapshot_file = {
                    "id": snapshot_file_id,
                    "current_path": str(snapshot_path),
                    "file_size": actual_size,
                }
                project_version_id = repo.insert_project_version_repo(
                    cursor, snapshot_file, user_id, 1
                )
                snapshot_files.append({
                    "submission_file_id": None,
                    "file_id": snapshot_file_id,
                    "source_file_id": file["id"],
                    "file_name": file["file_name"],
                    "project_version_id": project_version_id,
                    "file_size": actual_size,
                })

            repo.replace_submission_files_repo(
                cursor,
                submission_id,
                [item["file_id"] for item in snapshot_files],
            )
            linked_files = repo.list_submission_files_repo(
                cursor, submission_id
            )
            links_by_file_id = {
                link["file_id"]: link["submission_file_id"]
                for link in linked_files
            }
            for item in snapshot_files:
                item["submission_file_id"] = links_by_file_id[item["file_id"]]
            record_audit_event(
                cursor,
                user_id,
                "Submit" if existing is None else "Resubmit",
                "Submission",
                submission_id,
                f"Saved current submission for activity {activity_id}.",
            )
            result = {
                "submission_id": submission_id,
                "activity_id": activity_id,
                "project_id": project_id,
                "status": status,
                "submitted_at": _iso(now),
                "files": snapshot_files,
            }
        return result, 201 if existing is None else 200
    except Exception:
        for path in saved_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Could not remove a failed submission snapshot"
                )
        raise


def list_activity_submissions_service(user_id, role, activity_id):
    positive_id(activity_id, "activity_id")
    with submission_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        activity = repo.lock_activity_repo(cursor, activity_id)
        if activity is None:
            raise SubmissionError("Activity not found.", 404)
        if role == "Instructor" and activity["instructor_id"] != profile_id:
            raise SubmissionError("Activity not found.", 404)
        if role == "Student":
            membership = repo.student_membership_repo(
                cursor, activity["class_id"], user_id
            )
            if membership is None:
                raise SubmissionError("You are not enrolled in this class.", 403)
        rows = repo.list_activity_submissions_repo(
            cursor, activity_id, role, profile_id
        )
        for row in rows:
            row["submitted_at"] = _iso(row["submitted_at"])
            row["files"] = repo.list_submission_files_repo(
                cursor, row["submission_id"]
            )
        return rows


def list_submission_files_service(user_id, role, submission_id):
    positive_id(submission_id, "submission_id")
    with submission_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        submission = repo.submission_access_repo(cursor, submission_id)
        if submission is None:
            raise SubmissionError("Submission not found.", 404)
        if role == "Student" and submission["student_id"] != profile_id:
            raise SubmissionError("Submission not found.", 404)
        if role == "Instructor" and submission["instructor_id"] != profile_id:
            raise SubmissionError("Submission not found.", 404)
        return {
            "submission_id": submission_id,
            "activity_id": submission["activity_id"],
            "project_id": submission["project_id"],
            "submitted_at": _iso(submission["submitted_at"]),
            "status": submission["status"],
            "remarks": submission["remarks"],
            "files": repo.list_submission_files_repo(cursor, submission_id),
        }


def review_submission_service(
    user_id, role, submission_id, status, remarks
):
    positive_id(submission_id, "submission_id")
    if role not in ("Admin", "Instructor"):
        raise SubmissionError("Only instructors and Admins can review submissions.", 403)
    if status not in ("Returned", "Accepted", "Rejected"):
        raise SubmissionError("status must be Returned, Accepted, or Rejected.")
    if remarks is not None:
        if not isinstance(remarks, str):
            raise SubmissionError("remarks must be text no longer than 65535 bytes.")
        try:
            remarks_size = len(remarks.encode("utf-8"))
        except UnicodeEncodeError:
            raise SubmissionError("remarks must contain valid text.")
        if remarks_size > 65535:
            raise SubmissionError("remarks must be text no longer than 65535 bytes.")
        remarks = remarks.strip() or None

    with submission_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        if repo.lock_submission_repo(cursor, submission_id) is None:
            raise SubmissionError("Submission not found.", 404)
        submission = repo.submission_access_repo(cursor, submission_id)
        if submission is None:
            raise SubmissionError("Submission not found.", 404)
        if role == "Instructor" and submission["instructor_id"] != profile_id:
            raise SubmissionError("Submission not found.", 404)
        if submission["status"] in ("Accepted", "Rejected"):
            raise SubmissionError(
                f"A {submission['status'].lower()} submission cannot be reviewed again.",
                409,
            )

        new_status = status
        repo.update_submission_review_state_repo(
            cursor, submission_id, new_status, remarks
        )
        record_audit_event(
            cursor, user_id, "Review", "Submission", submission_id,
            f"Reviewed submission: {status}.",
        )
        return {
            "submission_id": submission_id,
            "status": status,
            "remarks": remarks,
        }


def get_submission_file_service(user_id, role, submission_id, submission_file_id):
    positive_id(submission_id, "submission_id")
    positive_id(submission_file_id, "submission_file_id")
    with submission_transaction() as cursor:
        submission = repo.submission_access_repo(cursor, submission_id)
        if submission is None:
            raise SubmissionError("Submission not found.", 404)
        _authorize_submission(cursor, user_id, role, submission)
        file = repo.submission_file_repo(
            cursor, submission_id, submission_file_id
        )
        if file is None:
            raise SubmissionError("Submitted file not found.", 404)
        path = _stored_project_file(
            file["student_id"], file["project_id"], file["file_path"]
        )
        return path, file["file_name"]
