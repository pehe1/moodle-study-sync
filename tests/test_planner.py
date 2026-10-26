import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from moodle_study_sync.planner import plan_sync


class PlannerTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent / ".tmp"
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        assert Path(self.directory.name).resolve().is_relative_to(scratch.resolve())
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file = self.root / "aula.pdf"
        self.file.write_bytes(b"synthetic study material")
        self.digest = hashlib.sha256(self.file.read_bytes()).hexdigest()

    def inventory(self, **changes):
        resource = {"resource_id": "10", "title": "Aula", "local_path": "aula.pdf", "sha256": self.digest}
        resource.update(changes)
        return {"course_id": "20", "google_notebook_id": "notebook-a", "resources": [resource]}

    def action(self, inventory):
        return plan_sync(inventory, self.root)["items"][0]["action"]

    def test_confirmed_receipt_avoids_reupload_on_repeated_plans(self):
        manifest = self.inventory(google_source_id="source-a", uploaded_sha256=self.digest,
                                  uploaded_notebook_id="notebook-a", google_upload_status="processed-and-cited")
        self.assertEqual(self.action(manifest), "recorded_current")
        self.assertEqual(plan_sync(manifest, self.root), plan_sync(manifest, self.root))

    def test_same_title_or_source_without_hash_requires_review(self):
        self.assertEqual(self.action(self.inventory(google_source_id="source-a")), "review_existing_version")

    def test_receipt_from_another_notebook_does_not_count(self):
        manifest = self.inventory(google_source_id="source-a", uploaded_sha256=self.digest,
                                  uploaded_notebook_id="notebook-b", google_upload_status="processed")
        self.assertEqual(self.action(manifest), "review_existing_version")

    def test_upload_with_uncertain_result_is_not_repeated(self):
        self.assertEqual(self.action(self.inventory(google_upload_status="uncertain")), "reconcile_in_flight")

    def test_modified_bytes_require_review(self):
        self.file.write_bytes(b"new edition")
        self.assertEqual(self.action(self.inventory(sha256=self.digest)), "review_changed_file")

    def test_duplicate_bytes_produce_one_upload(self):
        manifest = self.inventory()
        manifest["resources"].append(dict(manifest["resources"][0], resource_id="11", title="Outra aula"))
        self.assertEqual([item["action"] for item in plan_sync(manifest, self.root)["items"]],
                         ["upload", "duplicate_local_content"])

    def test_paths_cannot_escape_project(self):
        with self.assertRaises(ValueError):
            self.action(self.inventory(local_path="../outside.pdf"))

    def test_missing_file_and_duplicate_resource_ids(self):
        self.assertEqual(self.action(self.inventory(local_path="missing.pdf")), "missing_file")
        manifest = self.inventory()
        manifest["resources"].append(dict(manifest["resources"][0]))
        with self.assertRaises(ValueError):
            plan_sync(manifest, self.root)

    def test_long_windows_paths_remain_eligible(self):
        folder = self.root / ("a" * 120) / ("b" * 120)
        target = folder / "aula.pdf"
        extended_folder = Path("\\\\?\\" + str(folder)) if os.name == "nt" else folder
        extended_file = extended_folder / target.name
        extended_folder.mkdir(parents=True)
        extended_file.write_bytes(self.file.read_bytes())
        cleanup_target = self.root / ("a" * 120)
        self.assertTrue(cleanup_target.resolve().is_relative_to(self.root.resolve()))
        cleanup_path = Path("\\\\?\\" + str(cleanup_target)) if os.name == "nt" else cleanup_target
        self.addCleanup(shutil.rmtree, cleanup_path)
        manifest = self.inventory(local_path=target.relative_to(self.root).as_posix())
        self.assertEqual(self.action(manifest), "upload")


if __name__ == "__main__":
    unittest.main()
