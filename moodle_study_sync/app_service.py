"""Operações do app local. Nenhuma credencial é devolvida à interface."""

import asyncio
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import unicodedata

from filelock import FileLock, Timeout

from .google_sync import timestamp
from .moodle import discover_courses, read_config
from .run import google_client, execute
from .settings import load_app_settings, new_manifest, save_app_settings
from .storage import atomic_json, private_home, sync_lock


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, ValueError):
        return default


def sync_busy(root):
    try:
        with sync_lock(root):
            return False
    except Timeout:
        return True


def app_state(root):
    root = Path(root)
    settings = load_app_settings(root)
    groups = {}
    for course in settings["courses"]:
        key = course["semester"] + ":" + course["notebook_id"]
        group = groups.setdefault(key, {"key": key, "name": course["name"], "semester": course["semester"],
            "notebook_id": course["notebook_id"], "rooms": [], "resources": 0, "sources": 0,
            "legacy": 0, "local_only": 0, "enabled": False, "status": "pending", "issues": 0, "details": []})
        group["rooms"].append({"id": str(course["course_id"]), "name": course.get("room", "Teoria"), "enabled": course["enabled"]})
        group["enabled"] |= course["enabled"]
        inventory = read_json(root / course["inventory"], {})
        group["resources"] += sum(not item.get("moodle_removed") for item in inventory.get("resources", []))
        last = read_json(root / "private" / f"last-course-{course['course_id']}.json", {})
        group["sources"] = max(group["sources"], last.get("remote_source_count", 0))
        group["legacy"] += last.get("summary", {}).get("existing_preserved", 0)
        group["local_only"] += last.get("summary", {}).get("local_only", 0)
        for item in last.get("items", []):
            if item["action"] not in {"current", "uploaded", "uploaded_ocr", "uploaded_image", "reconciled", "existing_preserved", "associated_identical_content", "removed_from_moodle_preserved", "local_only"}:
                group["details"].append({"title": item["title"], "action": item["action"]})
        if last.get("error_type"):
            group["details"].append({"title": "A atualização foi interrompida e preservou o progresso.", "action": "retry"})
        if last:
            if last.get("status") != "ok": group["issues"] += 1
            group["status"] = "attention_required" if group["issues"] else "ok"
    runtime = read_json(root / "private" / "runtime.local.json", {})
    return {"groups": list(groups.values()), "schedule": runtime.get("daily_at", "23:00"),
            "busy": sync_busy(root), "progress": read_json(root / "private" / "progress.json", {}),
            "last_sync": read_json(root / "private" / "last-sync.json", {}),
            "connections": {"moodle": (private_home() / "moodle-dl" / "config.json").is_file(),
                            "google": (private_home() / "google" / "profiles" / "study-sync" / "storage_state.json").is_file()}}


def refresh_catalog(root):
    moodle = discover_courses()
    async def google():
        async with google_client() as client:
            return [{"id": row.id, "title": row.title} for row in await client.notebooks.list()]
    catalog = {"moodle": moodle, "notebooks": asyncio.run(google()), "checked_at_utc": timestamp()}
    atomic_json(Path(root) / "private" / "catalog.json", catalog)
    return catalog


def label(value, maximum=150):
    if not isinstance(value, str): raise ValueError("Preencha o nome e o semestre.")
    clean = " ".join(unicodedata.normalize("NFC", value).split())
    if not clean or len(clean) > maximum or clean in {".", ".."}:
        raise ValueError("Use um nome válido e mais curto.")
    return clean


def add_course(root, payload):
    root = Path(root)
    with sync_lock(root, timeout=2):
        settings = load_app_settings(root)
        identifier = str(payload.get("course_id", ""))
        if any(str(course["course_id"]) == identifier for course in settings["courses"]):
            raise ValueError("Esta sala já está cadastrada. Você pode reativá-la na biblioteca.")
        rows = discover_courses()
        row = next((course for course in rows if course["id"] == identifier), None)
        if row is None: raise ValueError("Esta matéria não está disponível na conta Moodle.")
        semester = label(payload.get("semester"), 60)
        name = label(payload.get("name") or row["name"])
        notebook_id = payload.get("notebook_id")

        async def destination():
            async with google_client() as client:
                if notebook_id:
                    # IDs só são aceitos se pertencem à lista acessível da conta.
                    notebooks = await client.notebooks.list()
                    notebook = next((n for n in notebooks if n.id == notebook_id), None)
                    if notebook is None: raise ValueError("Escolha um notebook disponível nesta conta.")
                    return notebook
                title = label(payload.get("notebook_title") or name)
                notebooks = await client.notebooks.list()
                existing = [n for n in notebooks if n.title.casefold() == title.casefold()]
                if len(existing) == 1: return existing[0]
                if len(existing) > 1: raise ValueError("Há notebooks com esse nome. Escolha um da lista.")
                intent_path = root / "private" / f"create-notebook-{identifier}.json"
                intent = read_json(intent_path, {})
                if intent.get("status") in {"intent", "uncertain"}:
                    raise ValueError("A criação anterior precisa ser conferida. Atualize a lista e escolha o notebook existente.")
                atomic_json(intent_path, {"status": "intent", "title": title, "started_at": timestamp()})
                try:
                    notebook = await client.notebooks.create(title)
                except Exception:
                    atomic_json(intent_path, {"status": "uncertain", "title": title})
                    raise
                atomic_json(intent_path, {"status": "confirmed", "title": title, "notebook_id": notebook.id})
                return notebook

        notebook = asyncio.run(destination())
        course = {"course_id": identifier, "name": name, "official_name": row["fullname"],
                  "room": row["room"], "semester": semester, "period": row["period"],
                  "notebook_id": notebook.id, "notebook_title": notebook.title,
                  "inventory": f"private/course-{identifier}.inventory.json", "enabled": True}
        target = root / course["inventory"]
        if target.exists():
            raise ValueError("Já existe um inventário desta sala; confira o cadastro anterior.")
        config = read_config()
        base_url = "https://" + config["moodle_domain"] + config["moodle_path"].rstrip("/")
        atomic_json(target, new_manifest(course, base_url))
        settings["courses"].append(course)
        save_app_settings(root, settings)
        # O catálogo é atualizado sem nova consulta; a próxima sincronização
        # atualiza a lista permitida do coletor com as matérias ativas.
        catalog = read_json(root / "private" / "catalog.json", {"moodle": rows, "notebooks": []})
        if not any(n["id"] == notebook.id for n in catalog["notebooks"]):
            catalog["notebooks"].append({"id": notebook.id, "title": notebook.title})
        atomic_json(root / "private" / "catalog.json", catalog)
        return {"message": "Matéria adicionada. Ela entra na próxima atualização automática."}


def toggle_group(root, payload):
    with sync_lock(root, timeout=2):
        settings = load_app_settings(root)
        matched = False
        if not isinstance(payload.get("enabled"), bool): raise ValueError("Estado inválido.")
        for course in settings["courses"]:
            if course["notebook_id"] == payload.get("notebook_id") and course["semester"] == payload.get("semester"):
                course["enabled"] = payload["enabled"]
                matched = True
        if not matched: raise ValueError("Matéria não encontrada.")
        save_app_settings(root, settings)
    return {"message": "Rotina da matéria atualizada."}


def connect_google(root):
    command = ["powershell.exe", "-NoLogo", "-NoProfile", "-File", str(Path(root) / "tools" / "Connect-Google.ps1"),
               "-PrivateHome", str(private_home())]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=1900, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode: raise PermissionError("A entrada Google não foi concluída.")
    refresh_catalog(root)
    return {"message": "Google conectado."}
