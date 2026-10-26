"""Prévia sem rede: compara arquivos com recibos persistidos do envio.

Um título igual não comprova igualdade de conteúdo. Recibos deste módulo
também não comprovam que uma fonte continua existindo no Google: o conector
deve conferir o destino antes de executar uma fila.
"""

from collections import Counter
import hashlib
import os
from pathlib import Path


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
READY_STATUSES = {"processed", "processed-and-cited"}


def _hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _filesystem_path(path):
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + str(path))
    return path


def plan_sync(inventory, root):
    """Retorna decisões locais sem alterar arquivos, inventário ou serviços."""
    root = Path(root).resolve()
    notebook_id = inventory.get("google_notebook_id")
    resources = inventory.get("resources", [])
    if not inventory.get("course_id") or not isinstance(resources, list):
        raise ValueError("Inventário sem identificação de curso ou lista de recursos.")
    ids = [(str(resource.get("resource_id", "")), resource.get("moodle_file_key", "")) for resource in resources]
    if any(not identifier[0] for identifier in ids) or len(ids) != len(set(ids)):
        raise ValueError("Cada recurso precisa de um ID único dentro do curso.")

    items = []
    for resource in resources:
        item = {"resource_id": str(resource["resource_id"]), "title": resource["title"]}
        source_id = resource.get("google_source_id")
        status = resource.get("google_upload_status")
        relative = resource.get("upload_path") or resource.get("local_path")
        if status in {"sending", "processing", "uncertain"}:
            item["action"] = "reconcile_in_flight"
        elif not relative:
            item["action"] = "review_existing_version" if source_id else "await_download"
        else:
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Arquivo fora da pasta do projeto: " + item["resource_id"])
            filesystem_path = _filesystem_path(path)
            if not filesystem_path.is_file():
                item["action"] = "missing_file"
            elif path.suffix.lower() not in ALLOWED_EXTENSIONS:
                item["action"] = "unsupported_format"
            else:
                digest = _hash(filesystem_path)
                item.update(path=str(path), sha256=digest)
                # Um recibo só vale para o curso/notebook e para os bytes enviados.
                receipt_matches = (
                    source_id
                    and notebook_id
                    and resource.get("uploaded_notebook_id") == notebook_id
                    and resource.get("uploaded_sha256") == digest
                    and status in READY_STATUSES
                )
                if receipt_matches:
                    item.update(action="recorded_current", source_id=source_id)
                elif source_id:
                    item.update(action="review_existing_version", source_id=source_id)
                elif resource.get("sha256") and resource["sha256"] != digest:
                    item["action"] = "review_changed_file"
                elif not notebook_id:
                    item["action"] = "associate_notebook"
                else:
                    item["action"] = "upload"
        items.append(item)

    # Um arquivo idêntico já enviado ao mesmo notebook pode representar dois
    # recursos Moodle. O conector deve registrar essa associação explicitamente.
    current_hashes = {item["sha256"]: item for item in items if item["action"] == "recorded_current"}
    pending_hashes = {}
    for item in items:
        if item["action"] != "upload":
            continue
        digest = item["sha256"]
        if digest in current_hashes:
            item.update(action="associate_identical_content", source_id=current_hashes[digest]["source_id"])
        elif digest in pending_hashes:
            item.update(action="duplicate_local_content", duplicate_of=pending_hashes[digest])
        else:
            pending_hashes[digest] = item["resource_id"]

    return {
        "schema_version": 1,
        "preview_only": True,
        "live_remote_state_verified": False,
        "course_id": str(inventory["course_id"]),
        "notebook_id": notebook_id,
        "summary": dict(Counter(item["action"] for item in items)),
        "items": items,
    }
