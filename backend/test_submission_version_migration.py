"""Disposable-MySQL verification for the V04 submission-version migration.

Run only with CLMS_TEST_DB_USER (and optional CLMS_TEST_DB_PASSWORD/HOST/PORT)
for an account allowed to CREATE and DROP databases. Never uses DB_NAME.
"""
import os
import unittest
import uuid
from pathlib import Path

import pymysql


DATABASE_DIR = Path(__file__).resolve().parent / "database"
MIGRATIONS = DATABASE_DIR / "migrations"


def sql_statements(path):
    """Split these line-terminated SQL scripts, respecting DELIMITER blocks."""
    delimiter = ";"
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper().startswith("DELIMITER "):
            if lines:
                raise ValueError("DELIMITER changed inside a statement")
            delimiter = stripped.split(None, 1)[1]
            continue
        lines.append(line)
        if stripped.endswith(delimiter):
            statement = "\n".join(lines)
            yield statement[: -len(delimiter)].strip()
            lines = []
    if lines:
        raise ValueError(f"Unterminated SQL statement in {path}")


class SubmissionVersionMigrationTests(unittest.TestCase):
    def test_constraints_and_legacy_resolution(self):
        user = os.getenv("CLMS_TEST_DB_USER")
        if not user:
            self.skipTest("Set CLMS_TEST_DB_USER for disposable MySQL verification")
        config = {
            "host": os.getenv("CLMS_TEST_DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("CLMS_TEST_DB_PORT", "3306")),
            "user": user,
            "password": os.getenv("CLMS_TEST_DB_PASSWORD", ""),
            "autocommit": True,
            "connect_timeout": 5,
        }
        database = "clms_pin_test_" + uuid.uuid4().hex[:12]
        admin = pymysql.connect(**config)
        created = False
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4")
            created = True
            with pymysql.connect(**config, database=database) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT VERSION()")
                    print("Disposable database server version:", cursor.fetchone()[0])
                    for statement in sql_statements(DATABASE_DIR / "Database_Design_V04.sql"):
                        cursor.execute(statement)
                    cursor.execute("""SELECT COUNT(*) FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA=%s
                          AND TABLE_NAME IN ('tblProjectFiles','tblProjectVersions','tblSubmissionFiles')
                          AND ENGINE='InnoDB'""", (database,))
                    self.assertEqual(cursor.fetchone()[0], 3)
                    cursor.execute("INSERT INTO tblRoles (role_name) VALUES ('Student'), ('Instructor')")
                    cursor.execute("""INSERT INTO tblUsers
                        (account_id,first_name,last_name,email,username,password_hash,role_id)
                        VALUES ('s1','Student','One','s1@example.test','s1','hash',1),
                               ('i1','Instructor','One','i1@example.test','i1','hash',2)""")
                    cursor.execute("""INSERT INTO tblStudents (user_id,student_number,program,year_level)
                        VALUES (1,'S1','CS',1)""")
                    cursor.execute("INSERT INTO tblInstructors (user_id,employee_number) VALUES (2,'I1')")
                    cursor.execute("""INSERT INTO tblClasses
                        (instructor_id,class_code,class_name,school_year,semester,created_at)
                        VALUES (1,'C1','Class 1','2026-2027','First Semester',NOW())""")
                    for number in range(1, 5):
                        cursor.execute("""INSERT INTO tblActivities
                            (class_id,instructor_id,activity_name,instructions,due_date,created_at)
                            VALUES (1,1,%s,'Do work',NOW(),NOW())""", (f"Activity {number}",))
                    cursor.execute("INSERT INTO tblProjects (student_id,project_name) VALUES (1,'Project')")
                    cursor.execute("""INSERT INTO tblProjectFiles
                        (project_id,file_name,file_size,current_path)
                        VALUES (1,'one.txt',3,'/test/one'), (1,'two.txt',3,'/test/two')""")
                    cursor.execute("""INSERT INTO tblProjectVersions
                        (file_id,version_number,file_path,file_size,created_by,created_at)
                        VALUES (1,1,'/test/one-v1',3,1,NOW())""")
                    for number in range(1, 5):
                        cursor.execute("""INSERT INTO tblSubmissions
                            (activity_id,student_id,submitted_at) VALUES (%s,1,NOW())""", (number,))
                    cursor.execute("INSERT INTO tblSubmissionFiles (submission_id,file_id) VALUES (1,1)")
                    # This controlled fixture submitted v1; v2 did not exist yet.
                    cursor.execute("""INSERT INTO tblProjectVersions
                        (file_id,version_number,file_path,file_size,created_by,created_at)
                        VALUES (1,2,'/test/one-v2',3,1,NOW()),
                               (2,1,'/test/two-v1',3,1,NOW())""")

                    for statement in sql_statements(MIGRATIONS / "001_submission_file_version_pin_prepare.sql"):
                        cursor.execute(statement)
                    cursor.execute("SELECT id, version_id FROM tblSubmissionFiles WHERE submission_id=1")
                    self.assertEqual(cursor.fetchone(), (1, None))
                    cursor.execute("""SELECT COUNT(*) FROM tblProjectVersions
                        WHERE file_id=1""")
                    self.assertEqual(cursor.fetchone()[0], 2)  # Ambiguous legacy link.

                    with self.assertRaises(pymysql.MySQLError) as unresolved:
                        for statement in sql_statements(MIGRATIONS / "002_submission_file_version_pin_enforce.sql"):
                            cursor.execute(statement)
                    self.assertIn("NULL", str(unresolved.exception).upper())
                    cursor.execute("SELECT version_id FROM tblSubmissionFiles WHERE id=1")
                    self.assertIsNone(cursor.fetchone()[0])
                    cursor.execute("""SELECT IS_NULLABLE FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='tblSubmissionFiles'
                              AND COLUMN_NAME='version_id'""", (database,))
                    self.assertEqual(cursor.fetchone()[0], "YES")

                    cursor.execute("""INSERT INTO tblSubmissionFiles
                        (submission_id,file_id,version_id) VALUES (2,1,1)""")
                    cursor.execute("""SELECT file_id, version_id FROM tblSubmissionFiles
                        WHERE submission_id=2""")
                    self.assertEqual(cursor.fetchone(), (1, 1))
                    for submission_id, file_id, version_id, expected_error in (
                        (3, 1, 99999, 1452),  # Unknown version.
                        (3, 1, 3, 1452),      # Version 3 belongs to file 2.
                        (2, 1, 2, 1062),      # Same submission and file, another version.
                        (3, 1, None, 1644),   # New link cannot be unpinned.
                    ):
                        with self.subTest(submission_id=submission_id, version_id=version_id):
                            with self.assertRaises(pymysql.MySQLError) as rejected:
                                cursor.execute("""INSERT INTO tblSubmissionFiles
                                    (submission_id,file_id,version_id) VALUES (%s,%s,%s)""",
                                               (submission_id, file_id, version_id))
                            self.assertEqual(rejected.exception.args[0], expected_error)
                    with self.assertRaises(pymysql.MySQLError) as deletion:
                        cursor.execute("DELETE FROM tblProjectVersions WHERE id=1")
                    self.assertEqual(deletion.exception.args[0], 1451)
                    cursor.execute("SELECT COUNT(*) FROM tblProjectVersions WHERE id=1")
                    self.assertEqual(cursor.fetchone()[0], 1)

                    # The fixture's controlled write order identifies v1 exactly.
                    # Production backfills still require independent evidence.
                    cursor.execute("UPDATE tblSubmissionFiles SET version_id=1 WHERE id=1")
                    cursor.execute("SELECT version_id FROM tblSubmissionFiles WHERE id=1")
                    self.assertEqual(cursor.fetchone()[0], 1)
                    for statement in sql_statements(MIGRATIONS / "002_submission_file_version_pin_enforce.sql"):
                        cursor.execute(statement)
                    cursor.execute("""SELECT IS_NULLABLE FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='tblSubmissionFiles'
                              AND COLUMN_NAME='version_id'""", (database,))
                    self.assertEqual(cursor.fetchone()[0], "NO")
                    cursor.execute("SELECT COUNT(*) FROM tblSubmissionFiles WHERE version_id IS NULL")
                    self.assertEqual(cursor.fetchone()[0], 0)
                    cursor.execute("SELECT COUNT(*) FROM tblSubmissionFiles")
                    self.assertEqual(cursor.fetchone()[0], 2)
        finally:
            if created:
                with admin.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE `{database}`")
            admin.close()
