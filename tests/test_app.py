from contextlib import asynccontextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moodle_study_sync.app import valid_api_request
from moodle_study_sync.app_service import add_course, toggle_group
from moodle_study_sync.settings import save_app_settings, load_app_settings
from moodle_study_sync.storage import atomic_json, sync_lock


class AppSecurityTest(unittest.TestCase):
    def test_fresh_checkout_can_open_an_empty_library(self):
        scratch = Path(__file__).parent / '.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            settings = load_app_settings(temporary)
            self.assertEqual(settings['courses'], [])
            self.assertEqual(settings['source_limit'], 50)
            self.assertEqual(load_app_settings(temporary), settings)

    def test_only_loopback_with_correct_token_can_access_data(self):
        self.assertTrue(valid_api_request('127.0.0.1:8000', 'http://127.0.0.1:8000', 'secret', 'secret', 8000))
        self.assertTrue(valid_api_request('127.0.0.1:8000', 'null', 'secret', 'secret', 8000))
        self.assertFalse(valid_api_request('evil.example:8000', None, 'secret', 'secret', 8000))
        self.assertFalse(valid_api_request('127.0.0.1:8000', 'https://evil.example', 'secret', 'secret', 8000))
        self.assertFalse(valid_api_request('127.0.0.1:8000', None, None, 'secret', 8000))


class AppCourseTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parent / '.tmp'
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        save_app_settings(self.root, {'schema_version': 2, 'source_limit': 50, 'courses': []})
        self.rows = [{'id': '12', 'fullname': 'Matéria de 2027/1', 'name': 'Matéria', 'period': '2027/1', 'room': 'Teoria'}]
        self.notebook = SimpleNamespace(id='existing-notebook', title='Meu notebook')
        self.create_calls = 0
        self.create_error = None

    @asynccontextmanager
    async def client(self):
        async def list_notebooks():
            return [self.notebook]
        async def create_notebook(title):
            self.create_calls += 1
            if self.create_error: raise self.create_error
            return SimpleNamespace(id='created-notebook', title=title)
        yield SimpleNamespace(notebooks=SimpleNamespace(list=list_notebooks, create=create_notebook))

    def add(self, **changes):
        payload = {'course_id': '12', 'semester': '6º SEMESTRE', 'name': 'Minha matéria', 'notebook_id': 'existing-notebook'}
        payload.update(changes)
        with patch('moodle_study_sync.app_service.discover_courses', return_value=self.rows), \
             patch('moodle_study_sync.app_service.google_client', self.client), \
             patch('moodle_study_sync.app_service.read_config', return_value={'moodle_domain': 'moodle.example', 'moodle_path': '/'}):
            return add_course(self.root, payload)

    def test_future_semester_can_use_existing_notebook_and_pause_without_deleting(self):
        self.add()
        course = load_app_settings(self.root)['courses'][0]
        self.assertEqual(course['semester'], '6º SEMESTRE')
        self.assertEqual(course['notebook_id'], 'existing-notebook')
        self.assertEqual(self.create_calls, 0)
        inventory = self.root / course['inventory']
        self.assertTrue(inventory.is_file())
        toggle_group(self.root, {'notebook_id': 'existing-notebook', 'semester': '6º SEMESTRE', 'enabled': False})
        self.assertFalse(load_app_settings(self.root)['courses'][0]['enabled'])
        self.assertTrue(inventory.is_file())

    def test_uncertain_notebook_creation_cannot_be_replayed(self):
        self.create_error = ConnectionError('unknown commit')
        with self.assertRaises(ConnectionError):
            self.add(notebook_id=None, notebook_title='Novo notebook')
        with self.assertRaises(ValueError):
            self.add(notebook_id=None, notebook_title='Novo notebook')
        self.assertEqual(self.create_calls, 1)

    def test_course_outside_account_is_not_accepted(self):
        with self.assertRaises(ValueError): self.add(course_id='999')
        self.assertEqual(load_app_settings(self.root)['courses'], [])


class AtomicStorageTest(unittest.TestCase):
    def test_panel_probes_preserve_lock_and_another_process_cannot_start(self):
        scratch = Path(__file__).parent / '.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root = Path(temporary).resolve()
            probe = 'from moodle_study_sync.app_service import sync_busy; import sys; print(sync_busy(sys.argv[1]))'
            for _ in range(3):
                check = subprocess.run([sys.executable, '-c', probe, str(root)], capture_output=True, text=True, timeout=15)
                self.assertEqual(check.returncode, 0, check.stderr)
                self.assertEqual(check.stdout.strip(), 'False')
            self.assertTrue((root / 'private/sync-v2.lock').is_file())
            with sync_lock(root):
                check = subprocess.run([sys.executable, '-c', probe, str(root)], capture_output=True, text=True, timeout=15)
                self.assertEqual(check.returncode, 0, check.stderr)
                self.assertEqual(check.stdout.strip(), 'True')
            with sync_lock(root, timeout=1):
                pass

    def test_reader_lock_does_not_lose_new_receipt(self):
        scratch = Path(__file__).parent / '.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            target = Path(temporary) / 'receipt.json'
            original = Path.replace
            attempts = []
            def replace(path, destination):
                attempts.append(1)
                if len(attempts) < 3: raise PermissionError('temporary Windows reader lock')
                return original(path, destination)
            with patch.object(Path, 'replace', replace): atomic_json(target, {'source_id': 'confirmed'})
            self.assertEqual(json.loads(target.read_text())['source_id'], 'confirmed')
            self.assertEqual(len(attempts), 3)


if __name__ == '__main__': unittest.main()
