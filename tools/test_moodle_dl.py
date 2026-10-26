"""Executa o coletor selecionado e verifica mudanças nos arquivos, sem expor a chave."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess


MATERIAL_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md", ".url"}


def snapshot(directory):
    directory = Path(directory).resolve()
    if os.name == "nt" and not str(directory).startswith("\\\\?\\"):
        directory = Path("\\\\?\\" + str(directory))
    files = {}
    for folder in directory.iterdir():
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in MATERIAL_EXTENSIONS:
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                files[path.relative_to(directory).as_posix()] = {"sha256": digest, "size_bytes": path.stat().st_size}
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--expected-course-id", type=int, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    state_dir = args.state_dir.resolve()
    with (state_dir / "config.json").open(encoding="utf-8") as source:
        config = json.load(source)
    if sorted(config.get("download_course_ids", [])) != sorted(args.expected_course_id):
        parser.error("O coletor deve estar limitado às matérias esperadas.")
    if any(config.get(key) for key in ("download_submissions", "download_forums", "download_also_with_cookie")):
        parser.error("Configuração fora do escopo do teste.")
    before = snapshot(state_dir)
    environment = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    executable = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "moodle-dl.exe"
    command = [str(executable), "--path", str(state_dir), "--max-path-length-workaround",
               "--max-parallel-api-calls", "2", "--max-parallel-downloads", "2", "--max-parallel-yt-dlp", "1"]
    process = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8",
                             errors="replace", env=environment, timeout=1200,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    after = snapshot(state_dir)
    output = process.stdout + process.stderr
    # A saída persistida não inclui a chave, mesmo em mensagens de erro.
    token = config.get("token", "")
    if token:
        output = output.replace(token, "[redigido]")
    output = re.sub(r"(?i)(token=)[^&\s]+", r"\1[redigido]", output)
    queued = re.findall(r"Download queue contains (\d+) tasks", output)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "moodle_dl_version": importlib.metadata.version("moodle-dl"),
        "course_ids": [str(value) for value in args.expected_course_id],
        "exit_code": process.returncode,
        "download_queue_tasks": int(queued[-1]) if queued else 0 if "No changes" in output else None,
        "files_before": len(before), "files_after": len(after),
        "new_files": len(after.keys() - before.keys()),
        "changed_files": sum(before[key] != after[key] for key in before.keys() & after.keys()),
        "missing_files": len(before.keys() - after.keys()),
        "extensions": dict(Counter(Path(name).suffix.lower() for name in after)),
        "total_bytes": sum(item["size_bytes"] for item in after.values()),
        "materials": after,
        "credential_location": "private-user-directory-outside-onedrive",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".log").write_text(output, encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "materials"}, ensure_ascii=True))
    raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()
