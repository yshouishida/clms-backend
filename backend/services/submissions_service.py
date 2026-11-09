"""Student submissions and owning-instructor review."""

from contextlib import contextmanager

from pymysql.err import IntegrityError

from backend.database.connection import get_connection
from backend.repositories import classes_repository as classes_repo
from backend.repositories import submissions_repository as repo
from backend.services.project_versions_service import read_file_version_service


class SubmissionError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


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


def submission_data(row, files=None):
    result = dict(row)
    for name in ("submitted_at", "due_date"):
        if name in result and hasattr(result[name], "isoformat"):
            result[name] = result[name].isoformat() + "Z"
    if files is not None:
        result["files"] = files
    return result


def student_id_for_user(cursor, user_id):
    profile = classes_repo.get_student_profile_repo(cursor, user_id)
    if profile is None:
        raise SubmissionError(
            "An active Student account is required.", 403
        )
    return profile["student_id"]


def instructor_id_for_user(cursor, user_id):
    profile = classes_repo.get_instructor_profile_repo(cursor, user_id)
    if profile is None:
        raise SubmissionError(
            "An active Instructor account is required.", 403
        )
    return profile["instructor_id"]


def validate_versions(version_ids):
    if not isinstance(version_ids, list) or not 1 <= len(version_ids) <= 100:
        raise SubmissionError(
            "version_ids must contain 1 to 100 version IDs."
        )
    for version_id in version_ids:
        positive_id(version_id, "version_id")
    if len(set(version_ids)) != len(version_ids):
        raise SubmissionError("version_ids must be distinct.")


def status_at_deadline(submitted_at, due_date):
    """V04 DATETIME values are UTC; equality is on time."""
    return "Late" if submitted_at > due_date else "Submitted"


def matching_retry(cursor, activity_id, student_id, project_id, version_ids):
    existing = repo.existing_submission_repo(
        cursor, activity_id, student_id, lock=True
    )
    if existing is None:
        return None

    files = repo.submission_files_repo(cursor, existing["id"])
    saved_version_ids = {row["version_id"] for row in files}

    if (
        existing["project_id"] != project_id
        or saved_version_ids != set(version_ids)
    ):
        raise SubmissionError(
            "A different submission already exists for this activity.",
            409,
        )

    return submission_data(existing, files)


def create_submission_service(user_id, activity_id, project_id, version_ids):
    positive_id(activity_id, "activity_id")
    positive_id(project_id, "project_id")
    validate_versions(version_ids)

    try:
        with submission_transaction() as cursor:
            student_id = student_id_for_user(cursor, user_id)
            activity = repo.activity_for_student_repo(
                cursor, activity_id, student_id
            )

            if (
                activity is None
                or activity["membership_status"] != "Enrolled"
            ):
                raise SubmissionError(
                    "Activity is unavailable to this student.", 404
                )

            retry = matching_retry(
                cursor, activity_id, student_id, project_id, version_ids
            )
            if retry is not None:
                return retry, 200

            if (
                activity["class_status"] != "Active"
                or activity["instructor_id"]
                != activity["class_instructor_id"]
            ):
                raise SubmissionError(
                    "Activity is not accepting submissions.", 409
                )

            if activity["status"] != "Published":
                raise SubmissionError(
                    "Activity is not accepting submissions.", 409
                )

            if repo.owned_project_repo(
                cursor, project_id, student_id
            ) is None:
                raise SubmissionError("Project not found.", 404)

            versions = repo.owned_versions_repo(
                cursor, version_ids, project_id, student_id
            )
            if (
                len(versions) != len(version_ids)
                or len({row["file_id"] for row in versions}) != len(versions)
            ):
                raise SubmissionError(
                    "Selected versions must be from distinct files "
                    "in your project.",
                    404,
                )

            for row in versions:
                read_file_version_service(row["version_id"])

            cursor.execute("SELECT UTC_TIMESTAMP() AS now_utc")
            submitted_at = cursor.fetchone()["now_utc"]
            status = status_at_deadline(
                submitted_at, activity["due_date"]
            )

            submission_id = repo.insert_submission_repo(
                cursor,
                activity_id,
                student_id,
                project_id,
                submitted_at,
                status,
            )

            for row in versions:
                repo.insert_submission_file_repo(
                    cursor,
                    submission_id,
                    row["file_id"],
                    row["version_id"],
                )

            saved = repo.existing_submission_repo(
                cursor, activity_id, student_id
            )
            if saved is None:
                raise RuntimeError(
                    "Created submission could not be retrieved."
                )

            files = repo.submission_files_repo(
                cursor, submission_id
            )
            return submission_data(saved, files), 201

    except IntegrityError as exc:
        if exc.args[0] != 1062:
            raise

        # The unique activity/student key settles concurrent attempts.
        with submission_transaction() as cursor:
            student_id = student_id_for_user(cursor, user_id)
            activity = repo.activity_for_student_repo(
                cursor, activity_id, student_id
            )

            if (
                activity is None
                or activity["membership_status"] != "Enrolled"
            ):
                raise SubmissionError(
                    "Activity is unavailable to this student.", 404
                )

            retry = matching_retry(
                cursor, activity_id, student_id, project_id, version_ids
            )
            if retry is None:
                raise SubmissionError(
                    "Concurrent submission; retry the request.", 409
                )

            return retry, 200


def list_submissions_service(user_id, activity_id):
    positive_id(activity_id, "activity_id")

    with submission_transaction() as cursor:
        instructor_id = instructor_id_for_user(cursor, user_id)

        if repo.instructor_activity_repo(
            cursor, activity_id, instructor_id
        ) is None:
            raise SubmissionError("Activity not found.", 404)

        rows = repo.instructor_submissions_repo(
            cursor, activity_id
        )
        return [submission_data(row) for row in rows]


def get_submission_service(user_id, submission_id):
    positive_id(submission_id, "submission_id")

    with submission_transaction() as cursor:
        instructor_id = instructor_id_for_user(cursor, user_id)
        row = repo.instructor_submission_repo(
            cursor, submission_id, instructor_id
        )
        if row is None:
            raise SubmissionError("Submission not found.", 404)

        files = repo.submission_files_repo(
            cursor, submission_id
        )
        return submission_data(row, files)


def review_submission_service(
    user_id, submission_id, status, remarks
):
    positive_id(submission_id, "submission_id")

    if status not in ("Returned", "Accepted", "Rejected"):
        raise SubmissionError(
            "Review status must be Returned, Accepted, or Rejected."
        )

    if remarks is not None:
        if not isinstance(remarks, str):
            raise SubmissionError(
                "remarks must be text or null."
            )
        try:
            remarks = remarks.strip()
            if len(remarks.encode("utf-8")) > 65535:
                raise SubmissionError(
                    "remarks exceed the database TEXT limit."
                )
        except UnicodeEncodeError:
            raise SubmissionError(
                "remarks contain invalid text."
            )

    with submission_transaction() as cursor:
        instructor_id = instructor_id_for_user(cursor, user_id)
        current = repo.instructor_submission_repo(
            cursor, submission_id, instructor_id, lock=True
        )
        if current is None:
            raise SubmissionError(
                "Submission not found.", 404
            )

        if current["status"] not in ("Submitted", "Late"):
            raise SubmissionError(
                "Submission has already been reviewed.", 409
            )

        repo.update_review_repo(
            cursor, submission_id, status, remarks
        )
        updated = repo.instructor_submission_repo(
            cursor, submission_id, instructor_id
        )
        files = repo.submission_files_repo(
            cursor, submission_id
        )
        return submission_data(updated, files)


def download_submission_file_service(
    user_id, submission_id, submission_file_id
):
    positive_id(submission_id, "submission_id")
    positive_id(submission_file_id, "submission_file_id")

    with submission_transaction() as cursor:
        instructor_id = instructor_id_for_user(cursor, user_id)

        if repo.instructor_submission_repo(
            cursor, submission_id, instructor_id
        ) is None:
            raise SubmissionError(
                "Submission not found.", 404
            )

        link = repo.submission_file_repo(
            cursor, submission_id, submission_file_id
        )
        if link is None:
            raise SubmissionError(
                "Submitted file not found.", 404
            )

        if link["version_id"] is None:
            raise SubmissionError(
                "Submitted file has no resolved version.", 409
            )

        version_id = link["version_id"]

    return read_file_version_service(version_id)