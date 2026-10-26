"""Persistência local durável, sem credenciais nos relatórios."""

import json
import os
import time
from pathlib import Path

from filelock import FileLock


def sync_lock(root, *, timeout=0):
    # O Windows pode manter um nome pendente de exclusão enquanto OneDrive
    # ou antivírus o observa. Conservar o arquivo evita esse estado entre
    # consultas do painel. A posse continua sendo um lock do SO, não a
    # existência do arquivo. O nome v2 substitui o antigo arquivo removível.
    path = Path(root) / "private" / "sync-v2.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(path, timeout=timeout, preserve_lock_file=True)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    # No Windows, o painel pode estar lendo o JSON no instante da troca.
    # Espera curta evita transformar esse acesso de leitura em falha do envio.
    for attempt in range(9):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 8:
                raise
            time.sleep(0.025 * (attempt + 1))


def private_home():
    if custom := os.environ.get("MOODLE_STUDY_SYNC_HOME"):
        return Path(custom).resolve()
    if os.name == "nt":
        return Path(os.environ["LOCALAPPDATA"]) / "MoodleStudySync"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "moodle-study-sync"
