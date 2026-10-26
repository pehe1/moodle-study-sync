"""Entrada sem janela do Agendador; mantém o resultado do processo de coleta."""

import os
from pathlib import Path
import subprocess
import sys

from .app_service import read_json
from .google_sync import timestamp
from .storage import atomic_json


def launch(root):
    root = Path(root).resolve()
    runtime = read_json(root / 'private/runtime.local.json', {})
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    if runtime.get('private_home'):
        environment['MOODLE_STUDY_SYNC_HOME'] = runtime['private_home']
    receipt = {'started_at_utc': timestamp(), 'status': 'running'}
    target = root / 'private/last-scheduled.json'
    atomic_json(target, receipt)
    executable = Path(sys.executable).with_name('python.exe') if os.name == 'nt' else Path(sys.executable)
    try:
        process = subprocess.run([str(executable), '-m', 'moodle_study_sync.run', '--max-uploads', '300'],
            cwd=root, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=7000,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        code = process.returncode
    except Exception as error:
        receipt['error_type'] = type(error).__name__
        code = 2
    receipt.update(status='ok' if code == 0 else 'attention_required', exit_code=code,
                   finished_at_utc=timestamp())
    atomic_json(target, receipt)
    return code


if __name__ == '__main__':
    raise SystemExit(launch(Path(__file__).resolve().parents[1]))
