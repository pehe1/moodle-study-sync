import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('public_release', PROJECT / 'tools/prepare_public_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PublicReleaseTest(unittest.TestCase):
    def test_private_data_and_conflict_copies_cannot_enter_archive(self):
        scratch = PROJECT / 'tests/.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root = Path(temporary)
            for name in ['README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'SECURITY.md']:
                (root / name).write_text('Synthetic public text', encoding='utf-8')
            (root / 'moodle_study_sync').mkdir()
            (root / 'moodle_study_sync/run.py').write_text('print("public")', encoding='utf-8')
            (root / 'moodle_study_sync/run (Edit conflict).py').write_text('private copy', encoding='utf-8')
            (root / 'private').mkdir()
            (root / 'private/storage_state.json').write_text('secret', encoding='utf-8')
            (root / 'sync.local.toml').write_text('secret', encoding='utf-8')
            (root / 'data').mkdir()
            (root / 'data/aula.pdf').write_bytes(b'private material')
            output = root / 'private/release.zip'
            manifest = release.build(root, output)
            self.assertEqual(len(manifest), 5)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), set(manifest) | {'release-manifest.json'})

    def test_credentials_in_an_allowed_source_file_block_release(self):
        scratch = PROJECT / 'tests/.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('token=' + 'a' * 32, encoding='utf-8')
            with self.assertRaises(ValueError):
                release.public_files(root)
