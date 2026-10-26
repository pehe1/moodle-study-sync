"""Configuração do app e migração do piloto de uma matéria."""

import json
from pathlib import Path
import tomllib

from .storage import atomic_json


def settings_file(root):
    return Path(root) / "private" / "app-settings.json"


def load_app_settings(root):
    path = settings_file(root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if not (Path(root) / "sync.local.toml").exists():
        result = {"schema_version": 2, "source_limit": 50, "courses": []}
        save_app_settings(root, result)
        return result
    old = tomllib.loads((Path(root) / "sync.local.toml").read_text(encoding="utf-8"))
    courses = []
    for course in old["courses"]:
        manifest = json.loads((Path(root) / course["inventory"]).read_text(encoding="utf-8"))
        courses.append(dict(course, semester=old["semester"], name=manifest["google_notebook_title"],
                            notebook_title=manifest["google_notebook_title"], room="Teoria"))
    result = {"schema_version": 2, "source_limit": old.get("source_limit", 50), "courses": courses}
    atomic_json(path, result)
    return result


def save_app_settings(root, settings):
    identifiers = [str(course["course_id"]) for course in settings["courses"]]
    if len(identifiers) != len(set(identifiers)) or any(not value.isdigit() for value in identifiers):
        raise ValueError("Matérias repetidas ou inválidas.")
    atomic_json(settings_file(root), settings)


def new_manifest(course, base_url):
    return {"schema_version": 1, "course_id": str(course["course_id"]),
            "official_course_name": course.get("official_name", course["name"]),
            "local_name": course["name"], "google_notebook_id": course["notebook_id"],
            "google_notebook_title": course["notebook_title"],
            "moodle_base_url": base_url, "room": course.get("room", "Teoria"), "resources": [], "resource_count": 0}
