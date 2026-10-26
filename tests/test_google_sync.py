import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moodle_study_sync.google_sync import sync_google
from moodle_study_sync.storage import atomic_json


def source(identifier, title="Arquivo enviado", ready=True):
    return SimpleNamespace(id=identifier, title=title, is_ready=ready)


class FakeGoogle:
    def __init__(self, initial=(), upload_error=None, wait_error=None, rename_error=None):
        self.remote = list(initial)
        self.upload_error = upload_error
        self.wait_error = wait_error
        self.rename_error = rename_error
        self.calls = 0
        self.notebooks = SimpleNamespace(get=self.get)
        self.sources = SimpleNamespace(list=self.list, add_file=self.add, wait_until_ready=self.wait, rename=self.rename)

    async def get(self, notebook):
        assert notebook == "destination"
        return SimpleNamespace(title="Matéria")

    async def list(self, notebook, strict=False):
        return list(self.remote)

    async def add(self, notebook, path, wait=False):
        self.calls += 1
        if self.upload_error:
            raise self.upload_error
        row = source("new-" + str(self.calls), path.name)
        self.remote.append(row)
        return row

    async def wait(self, notebook, identifier, timeout):
        if self.wait_error:
            raise self.wait_error
        return next(row for row in self.remote if row.id == identifier)

    async def rename(self, notebook, identifier, title):
        if self.rename_error:
            raise self.rename_error
        row = next(row for row in self.remote if row.id == identifier)
        row.title = title
        return row


class GoogleSyncTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        scratch = Path(__file__).parent / ".tmp"
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        path = self.root / "aula.pdf"
        path.write_bytes(b"synthetic material")
        self.digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.inventory_path = self.root / "inventory.json"
        self.journal = self.root / "journal.json"
        self.inventory = {"course_id": "10", "google_notebook_id": "destination",
                          "google_notebook_title": "Matéria", "resources": [
                              {"resource_id": "20", "title": "Aula", "local_path": "aula.pdf", "sha256": self.digest}]}
        atomic_json(self.inventory_path, self.inventory)

    async def run_sync(self, client):
        return await sync_google(client, self.inventory, self.root, self.inventory_path,
                                 self.journal, pause=0)

    async def test_second_run_uploads_nothing_and_preserves_manual_sources(self):
        manual = source("manual", "Anotações pessoais")
        client = FakeGoogle([manual])
        first = await self.run_sync(client)
        second = await self.run_sync(client)
        self.assertEqual(first["summary"], {"uploaded": 1})
        self.assertEqual(second["summary"], {"current": 1})
        self.assertEqual(client.calls, 1)
        self.assertIn(manual, client.remote)

    async def test_unknown_commit_is_never_replayed_even_with_matching_remote_title(self):
        client = FakeGoogle(upload_error=ConnectionError("connection lost after send"))
        await self.run_sync(client)
        client.upload_error = None
        client.remote.append(source("candidate", "aula.pdf"))
        second = await self.run_sync(client)
        self.assertEqual(client.calls, 1)
        self.assertEqual(second["summary"], {"uncertain_upload_review": 1})

    async def test_processing_timeout_resumes_same_source_without_uploading_again(self):
        client = FakeGoogle(wait_error=TimeoutError("still processing"))
        first = await self.run_sync(client)
        self.assertEqual(first["summary"], {"processing_pending_or_failed": 1})
        client.wait_error = None
        second = await self.run_sync(client)
        self.assertEqual(second["summary"], {"reconciled": 1})
        self.assertEqual(client.calls, 1)

    async def test_remote_manual_deletion_is_not_undone(self):
        client = FakeGoogle()
        await self.run_sync(client)
        client.remote.clear()
        report = await self.run_sync(client)
        self.assertEqual(report["summary"], {"remote_missing_or_not_ready_review": 1})
        self.assertEqual(client.calls, 1)

    async def test_new_version_keeps_prior_source_and_history(self):
        client = FakeGoogle()
        await self.run_sync(client)
        (self.root / "aula.pdf").write_bytes(b"revised version")
        item = self.inventory["resources"][0]
        item["sha256"] = hashlib.sha256(b"revised version").hexdigest()
        await self.run_sync(client)
        self.assertEqual(len(client.remote), 2)
        self.assertEqual(item["google_history"][0]["source_id"], "new-1")

    async def test_identical_resources_share_one_source(self):
        self.inventory["resources"].append(dict(self.inventory["resources"][0], resource_id="21"))
        client = FakeGoogle()
        report = await self.run_sync(client)
        self.assertEqual(report["summary"], {"uploaded": 1, "associated_identical_content": 1})
        self.assertEqual(client.calls, 1)

    async def test_partial_registration_is_not_adopted_as_success(self):
        error = RuntimeError("upload body failed")
        error.source_id = "partial"
        error.commit_state = SimpleNamespace(value="confirmed")
        client = FakeGoogle([source("partial", ready=False)], upload_error=error)
        await self.run_sync(client)
        client.upload_error = None
        client.remote[0].is_ready = True
        report = await self.run_sync(client)
        self.assertEqual(report["summary"], {"uncertain_upload_review": 1})
        self.assertNotIn("google_source_id", self.inventory["resources"][0])

    async def test_new_material_gets_readable_title_automatically(self):
        self.inventory["resources"][0]["title"] = "  Aula 02  -\n Me\u0301todo SCAMPER  "
        client = FakeGoogle()
        await self.run_sync(client)
        self.assertEqual(client.remote[0].title, "Aula 02 - Método SCAMPER")
        self.assertEqual(self.inventory["resources"][0]["google_source_title"], "Aula 02 - Método SCAMPER")

    async def test_title_failure_is_resumed_without_duplicate_upload(self):
        client = FakeGoogle(rename_error=ConnectionError("rename interrupted"))
        first = await self.run_sync(client)
        self.assertEqual(first["summary"]["title_update_pending"], 1)
        client.rename_error = None
        second = await self.run_sync(client)
        self.assertEqual(client.remote[0].title, "Aula")
        self.assertEqual(client.calls, 1)
        self.assertEqual(second["summary"], {"current": 1})

    async def test_later_manual_title_changes_are_preserved(self):
        client = FakeGoogle()
        await self.run_sync(client)
        client.remote[0].title = "Meu título de estudo"
        await self.run_sync(client)
        self.assertEqual(client.remote[0].title, "Meu título de estudo")

    async def test_legacy_source_is_preserved_without_claiming_matching_bytes(self):
        client = FakeGoogle([source('manual-old', 'aula.pdf')])
        report = await sync_google(client, self.inventory, self.root, self.inventory_path, self.journal,
                                   pause=0, adopt_existing=True)
        item = self.inventory['resources'][0]
        self.assertEqual(report['summary'], {'existing_preserved': 1})
        self.assertEqual(client.calls, 0)
        self.assertNotIn('uploaded_sha256', item)
        self.assertFalse(item['existing_content_hash_verified'])
        self.assertEqual(item['baseline_local_sha256'], self.digest)

    async def test_verified_content_from_another_room_is_not_uploaded_again(self):
        shared = dict(self.inventory['resources'][0], google_source_id='shared-source',
                      uploaded_sha256=self.digest, uploaded_notebook_id='destination', google_upload_status='processed')
        client = FakeGoogle([source('shared-source')])
        report = await sync_google(client, self.inventory, self.root, self.inventory_path, self.journal,
                                   pause=0, known_resources=[shared], adopt_existing=True)
        self.assertEqual(report['summary'], {'associated_identical_content': 1})
        self.assertEqual(client.calls, 0)

    async def test_processing_failure_of_one_file_does_not_stop_later_files(self):
        (self.root / 'second.pdf').write_bytes(b'other lecture')
        self.inventory['resources'].append({'resource_id':'21','title':'Outra aula','local_path':'second.pdf',
                                           'sha256':hashlib.sha256(b'other lecture').hexdigest()})
        client = FakeGoogle(wait_error=TimeoutError('still processing'))
        report = await self.run_sync(client)
        self.assertEqual(client.calls, 2)
        self.assertEqual(report['summary'], {'processing_pending_or_failed': 2})

    async def test_two_files_in_one_moodle_resource_keep_separate_receipts(self):
        self.inventory['resources'][0]['moodle_file_key'] = '/lecture.pdf'
        (self.root / 'answer.txt').write_text('Answer sheet', encoding='utf-8')
        self.inventory['resources'].append({'resource_id': '20', 'moodle_file_key': '/answer.txt',
            'title': 'Aula — Gabarito', 'local_path': 'answer.txt',
            'sha256': hashlib.sha256(b'Answer sheet').hexdigest()})
        client = FakeGoogle()
        first = await self.run_sync(client)
        self.assertEqual(first['summary'], {'uploaded': 2})
        self.assertEqual(len({i['google_source_id'] for i in self.inventory['resources']}), 2)
        second = await self.run_sync(client)
        self.assertEqual(second['summary'], {'current': 2})
        self.assertEqual(client.calls, 2)

    async def test_plan_pdf_can_be_sent_as_image_and_shared_without_repeating(self):
        class SourceProcessingError(Exception): pass
        client = FakeGoogle(wait_error=SourceProcessingError('rejected plan'))
        await self.run_sync(client)
        payload = self.root / 'plan.png'
        payload.write_bytes(b'\x89PNG\r\n\x1a\n' + b'image bytes' * 40)
        client.wait_error = None
        with patch('moodle_study_sync.google_sync.prepare_ocr', side_effect=ValueError('insufficient text')), patch('moodle_study_sync.google_sync.prepare_plan_image', return_value=payload):
            report = await self.run_sync(client)
        self.assertEqual(report['summary'], {'uploaded_image': 1})
        item = self.inventory['resources'][0]
        self.assertEqual(item['google_representation'], 'pdf-image')
        self.assertEqual(item['uploaded_sha256'], self.digest)
        self.assertNotEqual(item['uploaded_payload_sha256'], self.digest)
        self.assertIn('imagem da planta', client.remote[-1].title)
        await self.run_sync(client)
        self.assertEqual(client.calls, 2)
        journal = json.loads(self.journal.read_text(encoding='utf-8'))
        self.assertEqual(next(iter(journal['attempts'].values()))['failed_pdf_source_id'], 'new-1')

    async def test_scanned_pdf_can_be_read_as_text_without_repeating_after_success(self):
        class SourceProcessingError(Exception): pass
        client=FakeGoogle(wait_error=SourceProcessingError('rejected scan'))
        await self.run_sync(client)
        payload=self.root/'recognized.txt'
        payload.write_text('Recognized study material. '*30,encoding='utf-8')
        client.wait_error=None
        with patch('moodle_study_sync.google_sync.prepare_ocr',return_value=payload):
            report=await self.run_sync(client)
        self.assertEqual(report['summary'],{'uploaded_ocr':1})
        item=self.inventory['resources'][0]
        self.assertEqual(item['google_representation'],'ocr-text')
        self.assertEqual(item['uploaded_sha256'],self.digest)
        self.assertNotEqual(item['uploaded_payload_sha256'],self.digest)
        self.assertIn('texto reconhecido',client.remote[-1].title)
        await self.run_sync(client)
        self.assertEqual(client.calls,2)


if __name__ == "__main__":
    unittest.main()
