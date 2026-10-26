"""Catálogo de matérias usando somente a autorização local da instituição."""

import json
from pathlib import Path
import re
import requests

from .storage import atomic_json, private_home


def read_config():
    return json.loads((private_home() / "moodle-dl" / "config.json").read_text(encoding="utf-8"))


def call(function, **arguments):
    config = read_config()
    domain = config["moodle_domain"]
    if not re.fullmatch(r"[a-zA-Z0-9.-]+(?::\d+)?", domain):
        raise ValueError("Endereço da instituição inválido.")
    base = "https://" + domain + config["moodle_path"].rstrip("/")
    try:
        response = requests.post(base + "/webservice/rest/server.php", data={
            "wstoken": config["token"], "moodlewsrestformat": "json", "wsfunction": function, **arguments}, timeout=40)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        raise ConnectionError("Não foi possível consultar o Moodle.") from None
    if isinstance(data, dict) and data.get("exception"):
        raise PermissionError("O Moodle recusou a consulta. Reconecte sua conta.")
    return data


def discover_courses():
    user = call("core_webservice_get_site_info")
    rows = call("core_enrol_get_users_courses", userid=user["userid"])
    return [{"id": str(row["id"]), "fullname": row["fullname"],
             "name": re.split(r"\s*\[Turma", row["fullname"])[0].strip(),
             "period": (re.search(r"20\d{2}/[12]", row["fullname"]) or [""])[0],
             "room": "Prática" if re.search(r"\.\d{2}[A-Z]11(?:\||$)", row.get("shortname", "")) else "Teoria"}
            for row in rows]


def set_allowed_courses(course_ids):
    ids = sorted({int(value) for value in course_ids})
    if not ids or any(value <= 0 for value in ids):
        raise ValueError("Escolha pelo menos uma matéria.")
    path = private_home() / "moodle-dl" / "config.json"
    config = read_config()
    config["download_course_ids"] = ids
    # Nunca ampliar para discussões, notas, entregas ou sessão do navegador.
    for field in ("download_submissions", "download_forums", "download_quizzes", "download_lessons",
                  "download_workshops", "download_books", "download_databases", "download_calendars",
                  "download_descriptions", "download_links_in_descriptions", "download_linked_files",
                  "download_also_with_cookie"):
        config[field] = False
    atomic_json(path, config)
