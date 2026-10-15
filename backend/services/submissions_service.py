from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from backend.database.connection import get_connection
from backend.repositories import activities_repository
from backend.repositories import classes_repository
from backend.repositories import submissions_repository as repo
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


def _submission_version_data(cursor, version):
    result = dict(version)
    result["submitted_at"] = _iso(result["submitted_at"])
    result["files"] = [
        dict(row)
        for row in repo.list_submission_version_files_repo(cursor, version["id"])
    ]
    return result


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

    with submission_transaction() as cursor:
        activity = repo.lock_activity_repo(cursor, activity_id)
        if activity is None:
            raise SubmissionError("Activity not found.", 404)
        if activity["status"] != "Published":
            raise SubmissionError("This activity is not accepting submissions.", 409)

        membership = repo.student_membership_repo(
            cursor, activity["class_id"], user_id
        )
        if membership is None:
            raise SubmissionError("You are not enrolled in this class.", 403)
        student_id = membership["student_id"]

        if repo.owned_project_repo(cursor, project_id, student_id) is None:
            raise SubmissionError("Active project not found.", 404)
        files = repo.owned_project_files_repo(
            cursor, project_id, student_id, file_ids
        )
        if len(files) != len(file_ids):
            raise SubmissionError("One or more project files are unavailable.", 404)

        existing = repo.submission_repo(cursor, activity_id, student_id, lock=True)
        if existing and existing["status"] == "Accepted":
            raise SubmissionError("An accepted submission cannot be changed.", 409)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        status = "Late" if now > activity["due_date"] else "Submitted"
        if existing is None:
            submission_id = repo.create_submission_repo(
                cursor, activity_id, student_id, project_id, status
            )
            version_number = 1
        else:
            submission_id = existing["id"]
            versions = repo.list_submission_versions_repo(cursor, submission_id)
            version_number = max(
                (row["version_number"] for row in versions), default=0
            ) + 1
            repo.update_submission_repo(cursor, submission_id, project_id, status)

        snapshots = []
        for file in files:
            path = _stored_project_file(
                student_id, project_id, file["current_path"]
            )
            actual_size = path.stat().st_size
            if actual_size != file["file_size"]:
                raise SubmissionError(
                    f"Project file {file['file_name']} changed; reload and retry.",
                    409,
                )
            latest = repo.latest_project_version_repo(cursor, file["id"])
            if latest and latest["file_path"] == file["current_path"]:
                project_version_id = latest["id"]
            else:
                project_version_id = repo.insert_project_version_repo(
                    cursor, file, user_id,
                    latest["version_number"] + 1 if latest else 1,
                )
            snapshots.append((file, project_version_id))

        submission_version_id = repo.create_submission_version_repo(
            cursor, submission_id, version_number, status
        )
        for file, project_version_id in snapshots:
            repo.insert_submission_version_file_repo(
                cursor, submission_version_id, project_version_id, file
            )
        repo.replace_submission_files_repo(
            cursor, submission_id, [file["id"] for file in files]
        )

        return ({
            "submission_id": submission_id,
            "activity_id": activity_id,
            "project_id": project_id,
            "version_number": version_number,
            "status": status,
            "submitted_at": _iso(now),
            "files": [
                {
                    "file_id": file["id"],
                    "file_name": file["file_name"],
                    "project_version_id": project_version_id,
                    "file_size": file["file_size"],
                }
                for file, project_version_id in snapshots
            ],
        }, 201 if existing is None else 200)


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
        return rows


def list_submission_versions_service(user_id, role, submission_id):
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
        versions = repo.list_submission_versions_repo(cursor, submission_id)
        return {
            "submission_id": submission_id,
            "activity_id": submission["activity_id"],
            "status": submission["status"],
            "versions": [
                _submission_version_data(cursor, version) for version in versions
            ],
        }


def get_submission_file_service(
    user_id, role, submission_id, version_number, project_version_id
):
    positive_id(submission_id, "submission_id")
    positive_id(version_number, "version_number")
    positive_id(project_version_id, "project_version_id")
    with submission_transaction() as cursor:
        profile_id = _profile_id(cursor, user_id, role)
        submission = repo.submission_access_repo(cursor, submission_id)
        if submission is None:
            raise SubmissionError("Submission not found.", 404)
        _authorize_submission(cursor, user_id, role, submission)
        file = repo.submission_file_repo(
            cursor, submission_id, version_number, project_version_id
        )
        if file is None:
            raise SubmissionError("Submitted file not found.", 404)
        path = _stored_project_file(
            file["student_id"], file["project_id"], file["file_path"]
        )
        return path, file["file_name"]
