"""API integration test using a fresh, disposable V04 MySQL database.

Run with CLMS_TEST_DB_USER and optional CLMS_TEST_DB_PASSWORD/HOST/PORT.
The test creates and drops its own random database and isolated file storage.
"""
import io
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pymysql

from backend import create_app
from backend.database import connection as db_connection
from backend.test_submission_version_migration import DATABASE_DIR, MIGRATIONS, sql_statements
from backend.utils import jwt as jwt_utils
from backend.services.submissions_service import status_at_deadline


class SubmissionDeadlinePolicyTests(unittest.TestCase):
    def test_boundary_is_on_time(self):
        due = datetime(2026, 11, 9, 12, 0, 0)
        self.assertEqual(status_at_deadline(due, due), "Submitted")
        self.assertEqual(status_at_deadline(due - timedelta(microseconds=1), due), "Submitted")
        self.assertEqual(status_at_deadline(due + timedelta(microseconds=1), due), "Late")


class SubmissionWorkflowTests(unittest.TestCase):
    def setUp(self):
        user = os.getenv("CLMS_TEST_DB_USER")
        if not user:
            self.skipTest("Set CLMS_TEST_DB_USER for disposable MySQL API verification")
        self.config = {
            "host": os.getenv("CLMS_TEST_DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("CLMS_TEST_DB_PORT", "3306")),
            "user": user,
            "password": os.getenv("CLMS_TEST_DB_PASSWORD", ""),
            "autocommit": True,
            "connect_timeout": 5,
        }
        self.database = "clms_submission_test_" + uuid.uuid4().hex[:12]
        self.admin = pymysql.connect(**self.config)
        self.addCleanup(self.admin.close)
        with self.admin.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{self.database}` CHARACTER SET utf8mb4")
        self.addCleanup(self._drop_database)
        self.db = pymysql.connect(
            **self.config, database=self.database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        self.addCleanup(self.db.close)
        self.storage = tempfile.TemporaryDirectory(
            prefix="clms_submission_test_", dir=Path(__file__).resolve().parents[1]
        )
        self.addCleanup(self.storage.cleanup)
        self._install_schema_and_fixtures()
        db_patch = patch.dict(db_connection.DB_CONFIG, {
            "host": self.config["host"], "port": self.config["port"],
            "user": self.config["user"], "password": self.config["password"],
            "database": self.database,
        })
        db_patch.start()
        self.addCleanup(db_patch.stop)
        jwt_patch = patch.object(jwt_utils, "JWT_SECRET_KEY", "test-only-secret-12345678901234567890")
        jwt_patch.start()
        self.addCleanup(jwt_patch.stop)
        self.app = create_app()
        self.app.instance_path = self.storage.name
        self.app.testing = True
        self.client = self.app.test_client()
        self.student = self._auth(1, "Student")
        self.other_student = self._auth(2, "Student")
        self.instructor = self._auth(3, "Instructor")
        self.other_instructor = self._auth(4, "Instructor")

    def _drop_database(self):
        with self.admin.cursor() as cursor:
            cursor.execute(f"DROP DATABASE `{self.database}`")

    def _install_schema_and_fixtures(self):
        with self.db.cursor() as cursor:
            for statement in sql_statements(DATABASE_DIR / "Database_Design_V04.sql"):
                cursor.execute(statement)
            for name in (
                "001_submission_file_version_pin_prepare.sql",
                "002_submission_file_version_pin_enforce.sql",
            ):
                for statement in sql_statements(MIGRATIONS / name):
                    cursor.execute(statement)
            cursor.execute("INSERT INTO tblRoles (role_name) VALUES ('Student'), ('Instructor')")
            for number, role_id in ((1, 1), (2, 1), (3, 2), (4, 2)):
                cursor.execute("""INSERT INTO tblUsers
                    (account_id,first_name,last_name,email,username,password_hash,role_id)
                    VALUES (%s,'Test','User',%s,%s,'test-hash',%s)""",
                    (f"acct{number}", f"user{number}@example.test", f"user{number}", role_id))
            cursor.execute("""INSERT INTO tblStudents (user_id,student_number,program,year_level)
                VALUES (1,'S1','CS',1),(2,'S2','CS',1)""")
            cursor.execute("""INSERT INTO tblInstructors (user_id,employee_number)
                VALUES (3,'I1'),(4,'I2')""")
            cursor.execute("""INSERT INTO tblClasses
                (instructor_id,class_code,class_name,school_year,semester,created_at)
                VALUES (1,'C1','Class','2026-2027','First Semester',UTC_TIMESTAMP())""")
            cursor.execute("""INSERT INTO tblClassMembers
                (class_id,student_id,enrolled_at) VALUES (1,1,UTC_TIMESTAMP())""")
            for name, due, status in (
                ("On time", "UTC_TIMESTAMP() + INTERVAL 1 DAY", "Published"),
                ("Late", "UTC_TIMESTAMP() - INTERVAL 1 DAY", "Published"),
                ("Draft", "UTC_TIMESTAMP() + INTERVAL 1 DAY", "Draft"),
            ):
                cursor.execute(f"""INSERT INTO tblActivities
                    (class_id,instructor_id,activity_name,instructions,due_date,created_at,status)
                    VALUES (1,1,%s,'Submit work',{due},UTC_TIMESTAMP(),%s)""", (name, status))
            cursor.execute("""INSERT INTO tblFolders
                (student_id,folder_name,created_at) VALUES (1,'Project',UTC_TIMESTAMP())""")
            cursor.execute("""INSERT INTO tblProjects (student_id,folder_id,project_name)
                VALUES (1,1,'Main'),(1,1,'Other'),(2,NULL,'Someone else')""")

    def _auth(self, user_id, role):
        return {"Authorization": "Bearer " + jwt_utils.create_access_token(user_id, role)}

    def _upload(self, project_id, name, content):
        return self.client.post(
            f"/folders/1/projects/{project_id}/files",
            data={"file": (io.BytesIO(content), name)},
            content_type="multipart/form-data", headers=self.student,
        )

    def test_pinned_download_permissions_review_and_policy(self):
        original = b"version-one\x00student-data"
        replacement = b"version-two\x00different-data"
        uploaded = self._upload(1, "assignment.bin", original)
        self.assertEqual(uploaded.status_code, 201, uploaded.get_json())
        first_file = uploaded.get_json()["data"]["files"][0]
        file_id = first_file["id"]
        v1 = first_file["version"]["id"]
        self.assertEqual(first_file["version"]["version_number"], 1)

        body = {"project_id": 1, "version_ids": [v1]}
        denied_student = self.client.post(
            "/activities/1/submissions", json=body, headers=self.other_student
        )
        self.assertEqual(denied_student.status_code, 404, denied_student.get_json())
        wrong_project = self.client.post(
            "/activities/1/submissions",
            json={"project_id": 2, "version_ids": [v1]}, headers=self.student,
        )
        self.assertEqual(wrong_project.status_code, 404, wrong_project.get_json())
        draft = self.client.post(
            "/activities/3/submissions", json=body, headers=self.student
        )
        self.assertEqual(draft.status_code, 409, draft.get_json())

        submitted = self.client.post(
            "/activities/1/submissions", json=body, headers=self.student
        )
        self.assertEqual(submitted.status_code, 201, submitted.get_json())
        record = submitted.get_json()["data"]
        self.assertEqual(record["status"], "Submitted")
        self.assertEqual(record["files"][0]["version_id"], v1)
        submission_id = record["id"]
        link_id = record["files"][0]["submission_file_id"]
        retry = self.client.post(
            "/activities/1/submissions", json=body, headers=self.student
        )
        self.assertEqual(retry.status_code, 200, retry.get_json())
        self.assertEqual(retry.get_json()["data"]["id"], submission_id)

        replaced = self.client.post(
            f"/folders/1/projects/1/files/{file_id}/versions",
            data={"file": (io.BytesIO(replacement), "assignment.bin")},
            content_type="multipart/form-data", headers=self.student,
        )
        self.assertEqual(replaced.status_code, 201, replaced.get_json())
        v2 = replaced.get_json()["data"]["version"]["id"]
        self.assertNotEqual(v1, v2)
        self.assertEqual(replaced.get_json()["data"]["version"]["version_number"], 2)
        changed_attempt = self.client.post(
            "/activities/1/submissions",
            json={"project_id": 1, "version_ids": [v2]}, headers=self.student,
        )
        self.assertEqual(changed_attempt.status_code, 409, changed_attempt.get_json())

        own_list = self.client.get("/activities/1/submissions", headers=self.instructor)
        self.assertEqual(own_list.status_code, 200, own_list.get_json())
        self.assertEqual([row["id"] for row in own_list.get_json()["data"]], [submission_id])
        detail = self.client.get(f"/submissions/{submission_id}", headers=self.instructor)
        self.assertEqual(detail.status_code, 200, detail.get_json())
        self.assertEqual(detail.get_json()["data"]["files"][0]["version_id"], v1)
        url = f"/submissions/{submission_id}/files/{link_id}/content"
        denied_download = self.client.get(url, headers=self.other_instructor)
        self.assertEqual(denied_download.status_code, 404, denied_download.get_json())
        self.assertEqual(
            self.client.get(f"/submissions/{submission_id}", headers=self.other_instructor).status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/activities/1/submissions", headers=self.other_instructor).status_code,
            404,
        )
        pinned = self.client.get(url, headers=self.instructor)
        self.assertEqual(pinned.status_code, 200, pinned.get_json(silent=True))
        self.assertEqual(pinned.data, original)

        invalid_review = self.client.patch(
            f"/submissions/{submission_id}/review",
            json={"status": "Late"}, headers=self.instructor,
        )
        self.assertEqual(invalid_review.status_code, 400, invalid_review.get_json())
        denied_review = self.client.patch(
            f"/submissions/{submission_id}/review",
            json={"status": "Accepted"}, headers=self.other_instructor,
        )
        self.assertEqual(denied_review.status_code, 404, denied_review.get_json())
        reviewed = self.client.patch(
            f"/submissions/{submission_id}/review",
            json={"status": "Returned", "remarks": "Revise later"}, headers=self.instructor,
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.get_json())
        self.assertEqual(reviewed.get_json()["data"]["files"][0]["version_id"], v1)
        self.assertEqual(
            self.client.patch(
                f"/submissions/{submission_id}/review",
                json={"status": "Accepted"}, headers=self.instructor,
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post("/activities/1/submissions", json=body, headers=self.student).status_code,
            200,
        )

        late = self.client.post("/activities/2/submissions", json=body, headers=self.student)
        self.assertEqual(late.status_code, 201, late.get_json())
        self.assertEqual(late.get_json()["data"]["status"], "Late")
        late_link = late.get_json()["data"]["files"][0]["submission_file_id"]
        wrong_link = self.client.get(
            f"/submissions/{submission_id}/files/{late_link}/content",
            headers=self.instructor,
        )
        self.assertEqual(wrong_link.status_code, 404, wrong_link.get_json())
        with self.db.cursor() as cursor:
            cursor.execute("SELECT file_path FROM tblProjectVersions WHERE id=%s", (v1,))
            path = Path(cursor.fetchone()["file_path"])
            cursor.execute("SELECT COUNT(*) AS n FROM tblSubmissions WHERE activity_id=1")
            self.assertEqual(cursor.fetchone()["n"], 1)
        path.unlink()
        missing = self.client.get(url, headers=self.instructor)
        self.assertEqual(missing.status_code, 409, missing.get_json())
        self.assertIn("unavailable", missing.get_json()["message"].lower())
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE tblClassMembers SET status='Dropped' WHERE class_id=1 AND student_id=1")
        self.assertEqual(
            self.client.post("/activities/1/submissions", json=body, headers=self.student).status_code,
            404,
        )
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE tblUsers SET status='Disabled' WHERE id=1")
        self.assertEqual(
            self.client.post("/activities/1/submissions", json=body, headers=self.student).status_code,
            401,
        )
