"""Rotina independente: coleta única, biblioteca e notebooks de todas as matérias."""

import argparse
import asyncio
from collections import Counter
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tomllib
import traceback

from filelock import FileLock, Timeout

from .google_sync import sync_google, timestamp
from .moodle import set_allowed_courses
from .report import write_status
from .settings import load_app_settings
from .storage import atomic_json, private_home, sync_lock

ALLOWED_RESULTS = {"current", "uploaded", "reconciled", "existing_preserved",
                   "associated_identical_content", "removed_from_moodle_preserved", "local_only", "uploaded_ocr", "uploaded_image"}


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Arquivo da configuração fora do projeto.")
    return path


def load_settings(path, root):
    if path is None:
        settings = load_app_settings(root)
    elif Path(path).suffix == ".json":
        settings = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        settings = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    courses = [course for course in settings.get("courses", []) if course.get("enabled")]
    if settings.get("schema_version") not in {1, 2}:
        raise ValueError("Configuração incompatível.")
    ids = [str(course["course_id"]) for course in courses]
    if len(ids) != len(set(ids)):
        raise ValueError("Uma sala do Moodle não pode ser cadastrada duas vezes.")
    for course in courses:
        if not str(course["course_id"]).isdigit() or not course.get("notebook_id"):
            raise ValueError("Configure os IDs completos da matéria e do notebook.")
        manifest = json.loads(inside(root, course["inventory"]).read_text(encoding="utf-8"))
        if str(manifest["course_id"]) != str(course["course_id"]) or manifest["google_notebook_id"] != course["notebook_id"]:
            raise ValueError("IDs da configuração não correspondem ao inventário.")
        if not course.get("semester", settings.get("semester")):
            raise ValueError("Informe o semestre da matéria.")
    if not 1 <= settings.get("source_limit", 50) <= 300:
        raise ValueError("Limite de fontes inválido.")
    return settings, courses


def update_progress(root, **values):
    atomic_json(root / "private" / "progress.json", dict(updated_at_utc=timestamp(), **values))


def collect(root, state, course_ids):
    command = [sys.executable, str(root / "tools" / "test_moodle_dl.py"), "--state-dir", str(state),
               "--output", str(root / "private" / "last-collection.json")]
    for course_id in course_ids:
        command.extend(["--expected-course-id", str(course_id)])
    subprocess.run(command, check=True, cwd=root, timeout=1260,
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def import_materials(root, state, course, semester):
    command = [sys.executable, str(root / "tools" / "import_moodle_dl.py"), "--state-dir", str(state),
               "--inventory", str(inside(root, course["inventory"])), "--semester", semester,
               "--root", str(root), "--discover-new"]
    subprocess.run(command, check=True, cwd=root, timeout=300,
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def google_client():
    from notebooklm import NotebookLMClient
    from notebooklm.options import (ClientConfig, RuntimeOptions, RetryOptions, TransferOptions,
                                   WebBackendConfig, WebSessionOptions)
    home = private_home() / "google"
    storage = home / "profiles" / "study-sync" / "storage_state.json"
    if not storage.is_file():
        raise FileNotFoundError("Sessão Google ausente. Use Conectar Google no app.")
    os.environ["NOTEBOOKLM_HOME"] = str(home)
    os.environ["NOTEBOOKLM_PROFILE"] = "study-sync"
    os.environ.pop("NOTEBOOKLM_AUTH_JSON", None)
    logging.getLogger("notebooklm").setLevel(logging.CRITICAL)
    config = ClientConfig(backend=WebBackendConfig(session=WebSessionOptions(keepalive_interval=600)),
                          runtime=RuntimeOptions(max_concurrent_rpcs=2, operation_timeout=360),
                          retry=RetryOptions(rate_limit_max_retries=1, server_error_max_retries=1),
                          transfers=TransferOptions(max_concurrent_uploads=1))
    return NotebookLMClient.from_storage(path=str(storage), config=config)


async def send_all(root, settings, courses, max_uploads):
    inventories = {str(course["course_id"]): json.loads(inside(root, course["inventory"]).read_text(encoding="utf-8")) for course in courses}
    reports = []
    async with google_client() as client:
        for index, course in enumerate(courses):
            name = course.get("name", str(course["course_id"]))
            update_progress(root, phase="sending", course=name, course_id=str(course["course_id"]),
                            completed_courses=index, total_courses=len(courses), message="Conferindo e enviando materiais")
            shared = [item for other in courses if other["notebook_id"] == course["notebook_id"]
                      and other["course_id"] != course["course_id"] for item in inventories[str(other["course_id"])]["resources"]]
            try:
                report = await sync_google(client, inventories[str(course["course_id"])], root,
                        inside(root, course["inventory"]), root / "private" / f"google-journal-{course['course_id']}.json",
                        max_uploads=max_uploads, source_limit=settings.get("source_limit", 50),
                        known_resources=shared, adopt_existing=True,
                        progress=lambda resource, counts: update_progress(root, phase="sending", course=name,
                            course_id=str(course["course_id"]), completed_courses=index, total_courses=len(courses),
                            message="Organizando materiais no Google", processed_resource=resource, counts=counts))
                report["status"] = "ok" if set(report["summary"]) <= ALLOWED_RESULTS else "attention_required"
            except Exception as error:
                report = {"course_id": str(course["course_id"]), "notebook_id": course["notebook_id"],
                          "status": "attention_required", "error_type": type(error).__name__, "summary": {},
                          "error_file": Path(getattr(error, "filename", "") or "").name,
                          "error_errno": getattr(error, "errno", None),
                          "error_frames": [f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in traceback.extract_tb(error.__traceback__)]}
            report.update(name=name, semester=course.get("semester", settings.get("semester")), room=course.get("room", ""))
            reports.append(report)
            atomic_json(root / "private" / f"last-course-{course['course_id']}.json", report)
    return reports


def execute(root, *, config=None, max_uploads=300, collect_only=False, google_only=False):
    root = Path(root).resolve()
    report = {"started_at_utc": timestamp(), "status": "running", "courses": []}
    output = root / "private" / "last-sync.json"
    try:
        settings, courses = load_settings(config, root)
        runtime_file = root / "private" / "runtime.local.json"
        if runtime_file.exists():
            report["scheduled_daily_at"] = json.loads(runtime_file.read_text(encoding="utf-8-sig")).get("daily_at")
        with sync_lock(root, timeout=2):
            if not courses:
                report.update(status="ok", summary={}, message="Nenhuma matéria ativa.")
            else:
                if not google_only:
                    update_progress(root, phase="collecting", message="Procurando novidades no Moodle", total_courses=len(courses))
                    state = private_home() / "moodle-dl"
                    set_allowed_courses([course["course_id"] for course in courses])
                    collect(root, state, [course["course_id"] for course in courses])
                    for course in courses:
                        update_progress(root, phase="organizing", course=course.get("name"), message="Organizando a biblioteca por aula")
                        import_materials(root, state, course, course.get("semester", settings.get("semester")))
                if collect_only:
                    report.update(status="collection_ok", summary={})
                else:
                    reports = asyncio.run(send_all(root, settings, courses, max_uploads))
                    counts = Counter()
                    notebooks = {}
                    for row in reports:
                        counts.update(row.get("summary", {}))
                        if "remote_source_count" in row:
                            notebooks[row["notebook_id"]] = row["remote_source_count"]
                    report.update(courses=reports, summary=dict(counts), notebook_source_counts=notebooks,
                                  remote_source_count=sum(notebooks.values()),
                                  status="ok" if all(row["status"] == "ok" for row in reports) else "attention_required")
            report["finished_at_utc"] = timestamp()
            atomic_json(output, report)
            write_status(output.with_name("status.html"), report)
            update_progress(root, phase="done", status=report["status"], message="Atualização concluída")
    except Timeout:
        return {"status": "already_running"}, 4
    except Exception as error:
        report.update(status="attention_required", error_type=type(error).__name__, finished_at_utc=timestamp())
        atomic_json(output, report)
        write_status(output.with_name("status.html"), report)
        update_progress(root, phase="done", status="attention_required", message="A atualização precisa de atenção")
        return report, 2
    return report, 0 if report["status"] in {"ok", "collection_ok"} else 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--max-uploads", type=int, default=300)
    stages = parser.add_mutually_exclusive_group()
    stages.add_argument("--collect-only", action="store_true")
    stages.add_argument("--google-only", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.max_uploads <= 300:
        parser.error("O lote deve ter de zero a 300 envios por sala.")
    report, code = execute(Path(__file__).resolve().parents[1], config=args.config,
                           max_uploads=args.max_uploads, collect_only=args.collect_only, google_only=args.google_only)
    print(json.dumps({"status": report["status"], "summary": report.get("summary", {}),
                      "remote_source_count": report.get("remote_source_count")}, ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
