import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from moodle_study_sync.scheduled import launch


class ScheduledTest(unittest.TestCase):
    def test_scheduled_launcher_preserves_exit_status_and_private_location(self):
        scratch = Path(__file__).parent / '.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root = Path(temporary).resolve()
            (root / 'private').mkdir()
            (root / 'private/runtime.local.json').write_text(json.dumps({'private_home': 'private-user-location'}), encoding='utf-8')
            for code in [0, 3]:
                with patch('moodle_study_sync.scheduled.subprocess.run', return_value=SimpleNamespace(returncode=code)) as run:
                    self.assertEqual(launch(root), code)
                self.assertEqual(run.call_args.kwargs['env']['MOODLE_STUDY_SYNC_HOME'], 'private-user-location')
                self.assertEqual(run.call_args.kwargs['stdout'], subprocess.DEVNULL)
                receipt = json.loads((root / 'private/last-scheduled.json').read_text(encoding='utf-8'))
                self.assertEqual(receipt['status'], 'ok' if code == 0 else 'attention_required')
                self.assertEqual(receipt['exit_code'], code)
