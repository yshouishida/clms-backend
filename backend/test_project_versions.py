"""Service and storage checks without access to an application database."""
import copy
import io
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from backend.services import projectFiles_services as files
from backend.services import project_versions_service as versions
from backend.utils.folder_errors import FolderError


class ProjectVersionServiceTests(unittest.TestCase):
    def test_first_upload_replacement_legacy_and_failure_cleanup(self):
        workspace_instance = Path(__file__).resolve().parents[1] / "instance"
        workspace_instance.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=workspace_instance, prefix="version_test_") as storage:
            self.assertTrue(Path(storage).resolve().is_relative_to(workspace_instance.resolve()))
            app = Flask("version_test", instance_path=storage)
            app.config.update(PROJECT_UPLOAD_MAX_FILES=10, PROJECT_FILE_MAX_BYTES=1024,
                              PROJECT_UPLOAD_MAX_BYTES=10240)
            state = {"files": {}, "versions": {}, "file_id": 0, "version_id": 0}

            @contextmanager
            def transaction(user_id):
                self.assertEqual(user_id, 7)
                before = copy.deepcopy(state)
                try:
                    yield object(), 11
                except Exception:
                    state.clear()
                    state.update(before)
                    raise

            def insert_file(cursor, project_id, folder_id, name, mime, size, path):
                state["file_id"] += 1
                row = dict(id=state["file_id"], project_id=project_id, folder_id=folder_id,
                           file_name=name, file_type=mime, file_size=size, current_path=path,
                           created_at=datetime.now(), updated_at=datetime.now(),
                           status="Active", deleted_at=None)
                state["files"][row["id"]] = row
                return {key: value for key, value in row.items()
                        if key not in ("current_path", "deleted_at")}

            def insert_version(cursor, file_id, number, path, size, user_id):
                state["version_id"] += 1
                row = dict(id=state["version_id"], file_id=file_id, version_number=number,
                           file_path=path, file_size=size, created_by=user_id,
                           created_at=datetime.now())
                state["versions"][row["id"]] = row
                return {key: value for key, value in row.items() if key != "file_path"}

            def owned_file(cursor, student_id, folder_id, project_id, file_id):
                row = state["files"].get(file_id)
                if row and student_id == 11 and row["folder_id"] == folder_id and row["project_id"] == project_id:
                    return dict(row)
                return None

            def stored_version(cursor, version_id):
                row = state["versions"].get(version_id)
                return dict(row, file_name=state["files"][row["file_id"]]["file_name"]) if row else None

            class FakeConnection:
                def cursor(self): return self
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def close(self): pass

            def upload(name, content):
                return SimpleNamespace(filename=name, mimetype="application/octet-stream",
                                       stream=io.BytesIO(content))

            with ExitStack() as patches, app.app_context():
                for module in (files, versions):
                    patches.enter_context(patch.object(module, "student_transaction", transaction))
                patches.enter_context(patch.object(files.folders_repo, "get_active_folder_repo",
                                                   return_value=({"folder_name": "Project"}, 1)))
                patches.enter_context(patch.object(files.folders_repo, "root_key", return_value="PROJECT"))
                patches.enter_context(patch.object(files.files_repo, "get_active_project_repo",
                                                   return_value={"id": 23}))
                patches.enter_context(patch.object(files.files_repo, "file_name_exists_repo",
                                                   side_effect=lambda c, p, n: any(f["file_name"] == n for f in state["files"].values())))
                patches.enter_context(patch.object(files.files_repo, "insert_project_file_repo",
                                                   side_effect=insert_file))
                patches.enter_context(patch.object(versions.repo, "insert_version_repo",
                                                   side_effect=insert_version))
                patches.enter_context(patch.object(versions.repo, "get_owned_file_repo",
                                                   side_effect=owned_file))
                patches.enter_context(patch.object(versions.repo, "latest_version_number_repo",
                                                   side_effect=lambda c, f: max((v["version_number"] for v in state["versions"].values() if v["file_id"] == f), default=0)))
                patches.enter_context(patch.object(versions.repo, "update_current_file_repo",
                                                   side_effect=lambda c, f, p, s, m: state["files"][f].update(current_path=p, file_size=s, file_type=m)))
                patches.enter_context(patch.object(versions.repo, "get_stored_version_repo",
                                                   side_effect=stored_version))
                patches.enter_context(patch.object(versions.repo, "stored_path_is_referenced_repo",
                                                   side_effect=lambda p: any(v["file_path"] == str(p) for v in state["versions"].values()) or any(f["current_path"] == str(p) for f in state["files"].values())))
                patches.enter_context(patch.object(versions, "get_connection", return_value=FakeConnection()))

                original = b"original v1\x00content"
                created = files.upload_project_files_service(7, 3, 23, [upload("sample.bin", original)])["files"][0]
                file_id, v1 = created["id"], created["version"]["id"]
                self.assertEqual(created["version"]["version_number"], 1)
                self.assertEqual(len(state["versions"]), 1)
                replaced = versions.upload_file_version_service(7, 3, 23, file_id,
                                                                upload("sample.bin", b"replacement v2"))
                self.assertEqual(replaced["version"]["version_number"], 2)
                self.assertEqual(len(state["versions"]), 2)
                self.assertEqual(versions.read_file_version_service(v1)["content"], original)
                self.assertNotEqual(state["versions"][v1]["file_path"],
                                    state["versions"][replaced["version"]["id"]]["file_path"])

                directory = Path(storage) / "project_uploads" / "11" / "23"
                legacy_path = directory / "legacy"
                legacy_path.write_bytes(b"legacy v1")
                legacy_id = insert_file(None, 23, 3, "legacy.bin", "application/octet-stream",
                                        9, str(legacy_path))["id"]
                updated = versions.upload_file_version_service(7, 3, 23, legacy_id,
                                                               upload("legacy.bin", b"legacy v2"))
                self.assertEqual(updated["version"]["version_number"], 2)
                legacy_v1 = next(v for v in state["versions"].values()
                                 if v["file_id"] == legacy_id and v["version_number"] == 1)
                self.assertEqual(versions.read_file_version_service(legacy_v1["id"])["content"], b"legacy v1")

                before_paths = set(directory.iterdir())
                before_counts = len(state["files"]), len(state["versions"])
                with patch.object(versions.repo, "insert_version_repo", side_effect=RuntimeError("simulated DB failure")):
                    with self.assertRaises(RuntimeError):
                        files.upload_project_files_service(7, 3, 23, [upload("failed.bin", b"bad")])
                    with self.assertRaises(RuntimeError):
                        versions.upload_file_version_service(7, 3, 23, file_id,
                                                             upload("sample.bin", b"bad replacement"))
                self.assertEqual((len(state["files"]), len(state["versions"])), before_counts)
                self.assertEqual(set(directory.iterdir()), before_paths)
                self.assertEqual(versions.read_file_version_service(v1)["content"], original)

                with patch.object(files.os, "fsync", side_effect=OSError("simulated storage failure")):
                    with self.assertRaises(OSError):
                        files.upload_project_files_service(7, 3, 23,
                                                          [upload("storage-failed.bin", b"partial")])
                self.assertEqual((len(state["files"]), len(state["versions"])), before_counts)
                self.assertEqual(set(directory.iterdir()), before_paths)

                @contextmanager
                def lost_commit_acknowledgement(user_id):
                    yield object(), 11
                    raise RuntimeError("simulated lost commit acknowledgement")

                with patch.object(files, "student_transaction", lost_commit_acknowledgement):
                    with self.assertRaises(RuntimeError):
                        files.upload_project_files_service(7, 3, 23,
                                                          [upload("committed.bin", b"committed bytes")])
                committed = next(f for f in state["files"].values()
                                 if f["file_name"] == "committed.bin")
                self.assertTrue(Path(committed["current_path"]).is_file())
                committed_version = next(v for v in state["versions"].values()
                                         if v["file_id"] == committed["id"])
                self.assertEqual(versions.read_file_version_service(committed_version["id"])["content"],
                                 b"committed bytes")

                Path(state["versions"][v1]["file_path"]).unlink()
                with self.assertRaises(FolderError) as missing:
                    versions.read_file_version_service(v1)
                self.assertEqual(missing.exception.status_code, 409)
