"""Importa os recursos selecionados do catálogo do Moodle-DL para a biblioteca."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time


def filesystem_path(path):
    path = Path(path)
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(path.resolve()))
    return path


def digest(path):
    with filesystem_path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def safe_name(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip().rstrip(". ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--semester", required=True)
    parser.add_argument("--discover-new", action="store_true", help="Descobrir novos recursos de arquivo da matéria selecionada.")
    args = parser.parse_args()
    root = args.root.resolve()
    logical_state = args.state_dir.absolute()
    state = args.state_dir.resolve()
    manifest = json.loads(args.inventory.read_text(encoding="utf-8"))
    databases = list(state.rglob("moodle_state.db"))
    if len(databases) != 1:
        parser.error("Não foi possível identificar um único catálogo do coletor.")
    connection = sqlite3.connect(databases[0].as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT * FROM files "
            "WHERE course_id=? AND module_modname='resource' AND deleted=0 ORDER BY time_stamp DESC",
            (int(manifest["course_id"]),),
        ).fetchall()
    finally:
        connection.close()
    saved = {}
    def file_key(row):
        filename = row["content_filename"] if "content_filename" in row.keys() else Path(row["saved_to"]).name
        folder = row["content_filepath"] if "content_filepath" in row.keys() else "/"
        return (folder or "/").rstrip("/") + "/" + filename

    for row in rows:
        identifier = str(row["module_id"])
        identity = (identifier, file_key(row))
        # Um recurso Moodle pode oferecer lista e gabarito, por exemplo.
        # Cada arquivo tem identidade própria; versões anteriores do mesmo
        # arquivo continuam selecionadas pela data, sem escolha arbitrária.
        if identity in saved:
            prior = saved[identity]
            if prior["time_stamp"] == row["time_stamp"] and prior["saved_to"] != row["saved_to"]:
                parser.error("Recurso com mais de um arquivo simultâneo; revisar: " + identifier)
            continue
        saved[identity] = row
    for item in manifest["resources"]:
        if item.get("moodle_file_key"):
            continue
        matches = [(identity, row) for identity, row in saved.items() if identity[0] == str(item["resource_id"])]
        if len(matches) > 1:
            previous_name = Path(item.get("local_path", "")).name.split("--", 1)[-1]
            matches = [(identity, row) for identity, row in matches if Path(row["saved_to"]).name == previous_name]
            if len(matches) != 1:
                parser.error("Não foi possível associar o recibo anterior a um dos arquivos: " + str(item["resource_id"]))
        if matches:
            item["moodle_file_key"] = matches[0][0][1]
    discovered = 0
    if args.discover_new:
        existing = {(str(item["resource_id"]), item.get("moodle_file_key")): item for item in manifest["resources"]}
        sizes = {}
        for identifier, _ in saved: sizes[identifier] = sizes.get(identifier, 0) + 1
        for identity, row in saved.items():
            identifier, filename = identity
            title = row["module_name"] + (" — " + Path(row["saved_to"]).name if sizes[identifier] > 1 else "")
            if identity not in existing:
                item = {"resource_id": identifier, "moodle_file_key": filename, "title": title,
                        "section": row["section_name"],
                        "source_url": manifest.get("moodle_base_url", "https://moodle.example.invalid").rstrip("/") + "/mod/resource/view.php?id=" + identifier}
                manifest["resources"].append(item)
                discovered += 1
            else:
                existing[identity].update(title=title, section=row["section_name"])
        for item in manifest["resources"]:
            item["moodle_removed"] = (str(item["resource_id"]), item.get("moodle_file_key")) not in saved
        manifest["resource_count"] = len(saved)
    copied = kept = 0
    missing = []
    for item in manifest["resources"]:
        row = saved.get((str(item["resource_id"]), item.get("moodle_file_key")))
        if row is None:
            if not item.get("moodle_removed"):
                missing.append(str(item["resource_id"]))
            continue
        stored_path = Path(str(row["saved_to"]).removeprefix("\\\\?\\"))
        # Aplicativos Windows empacotados podem redirecionar AppData. O
        # catálogo guarda o caminho lógico usado na primeira execução.
        aliases = [logical_state, state]
        if os.name == "nt":
            aliases.append(Path(os.environ["USERPROFILE"]) / "AppData" / "Local" / "MoodleStudySync" / "moodle-dl")
        matching = next((alias for alias in aliases if stored_path.is_relative_to(alias)), None)
        if matching is None:
            parser.error("Arquivo do catálogo fora do diretório do coletor.")
        candidate = state / stored_path.relative_to(matching)
        source = Path(str(filesystem_path(candidate).resolve()).removeprefix("\\\\?\\"))
        if not source.is_relative_to(state) or not filesystem_path(source).is_file():
            parser.error("Arquivo do catálogo fora do local esperado ou ausente: " + str(item["resource_id"]))
        checksum = digest(source)
        folder = root / "data" / "materials" / safe_name(args.semester) / safe_name(manifest["local_name"]) / safe_name(item["section"])
        if manifest.get("room") == "Prática":
            folder = folder.parent / "Prática" / folder.name
        destination = folder / (str(item["resource_id"]) + "--" + source.name)
        if not destination.resolve().is_relative_to(root):
            parser.error("Destino fora da biblioteca do projeto.")
        filesystem_path(folder).mkdir(parents=True, exist_ok=True)
        if filesystem_path(destination).exists() and digest(destination) != checksum:
            destination = destination.with_name(destination.stem + "--" + checksum[:12] + destination.suffix)
        if filesystem_path(destination).exists():
            if digest(destination) != checksum:
                parser.error("Conflito de versões na biblioteca.")
            kept += 1
        else:
            shutil.copy2(filesystem_path(source), filesystem_path(destination))
            copied += 1
        if digest(destination) != checksum:
            parser.error("A cópia não corresponde ao download.")
        item.update(status="downloaded", local_path=destination.relative_to(root).as_posix(),
                    sha256=checksum, size_bytes=filesystem_path(source).stat().st_size,
                    collector="moodle-dl", collector_version="2.3.13")
        # Uma cópia preparada para upload em um piloto anterior pode conter
        # uma versão antiga; a prévia deve passar a avaliar o original atual.
        item.pop("upload_path", None)
    manifest.update(collection_method="moodle-dl-mobile-api", api_verified=True,
                    resource_download_count=sum(item.get("status") == "downloaded" and not item.get("moodle_removed") for item in manifest["resources"]))
    temporary = args.inventory.with_name(args.inventory.name + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for attempt in range(9):
        try:
            temporary.replace(args.inventory)
            break
        except PermissionError:
            if attempt == 8:
                raise
            time.sleep(0.025 * (attempt + 1))
    print(json.dumps({"matched_resources": copied + kept, "discovered_resources": discovered, "copied": copied, "already_present": kept,
                      "unmatched_resource_ids": missing}, ensure_ascii=True))
    if missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
