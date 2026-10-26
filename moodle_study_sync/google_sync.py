"""Envio sequencial com recibo durável e consulta remota antes de cada lote.

Um timeout não autoriza repetir a criação. Somente IDs retornados pelo envio
completo podem ser conciliados automaticamente; títulos iguais são indícios.
"""

import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import unicodedata

from .planner import ALLOWED_EXTENSIONS, _filesystem_path
from .storage import atomic_json
from .ocr import prepare_ocr, prepare_plan_image, is_scanned_pdf


def checksum(path):
    with _filesystem_path(Path(path)).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def source_display_title(item, *, updated=False):
    """Conserva o título da aula e os acentos; limpa espaços da coleta."""
    title = " ".join(unicodedata.normalize("NFC", item["title"]).split())
    if not title:
        title = "Material de estudo"
    suffix = " (versão atualizada)" if updated else ""
    return title[:200 - len(suffix)].rstrip() + suffix


def title_key(value):
    value = re.sub(r"\.(pdf|docx?|pptx?|txt|md)$", "", value.strip(), flags=re.I)
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in value if character.isalnum())


async def sync_google(client, inventory, root, inventory_path, journal_path, *,
                      max_uploads=5, source_limit=300, wait_timeout=180, pause=2,
                      known_resources=(), adopt_existing=False, progress=None):
    """Sincroniza apenas um notebook explicitamente associado ao inventário.

    O chamador deve manter um lock exclusivo durante coleta/importação/envio.
    Não apaga fontes; remoção manual no Google requer revisão explícita.
    """
    import json

    root = Path(root).resolve()
    notebook_id = inventory["google_notebook_id"]
    course_id = str(inventory["course_id"])
    expected_title = inventory["google_notebook_title"]
    if not course_id.isdigit() or any(not str(item["resource_id"]).isdigit() for item in inventory["resources"]):
        raise ValueError("IDs de curso e recurso devem ser numéricos.")
    if len({(str(item["resource_id"]), item.get("moodle_file_key", "")) for item in inventory["resources"]}) != len(inventory["resources"]):
        raise ValueError("IDs de recurso duplicados no inventário.")
    notebook = await client.notebooks.get(notebook_id)
    if notebook.title != expected_title:
        raise ValueError("O nome do notebook mudou; conferir a associação antes de enviar.")
    remote = {source.id: source for source in await client.sources.list(notebook_id, strict=True)}
    journal_path = Path(journal_path)
    journal = json.loads(journal_path.read_text(encoding="utf-8")) if journal_path.exists() else {
        "schema_version": 1, "course_id": course_id, "notebook_id": notebook_id, "attempts": {}}
    if journal["course_id"] != course_id or journal["notebook_id"] != notebook_id:
        raise ValueError("O diário pertence a outro curso ou notebook.")
    counts = Counter()
    results = []
    content_receipts = {}
    content_formats = {}

    def result(item, action):
        counts[action] += 1
        results.append({"resource_id": str(item["resource_id"]), "title": item["title"], "action": action})

    def save_journal():
        atomic_json(journal_path, journal)

    def receipt(item, digest, source, metadata=None):
        previous = item.get("google_source_id")
        if previous and previous != source.id:
            item.setdefault("google_history", []).append({
                "source_id": previous, "sha256": item.get("uploaded_sha256"),
                "notebook_id": item.get("uploaded_notebook_id"), "superseded_at": timestamp()})
        item.update(google_source_id=source.id, google_source_title=source.title,
                    google_upload_status="processed", uploaded_sha256=digest,
                    uploaded_notebook_id=notebook_id, uploaded_at=timestamp())
        metadata = metadata or content_formats.get(digest, {})
        item["google_representation"] = metadata.get("representation", "original")
        item["uploaded_payload_sha256"] = metadata.get("payload_sha256", digest)
        atomic_json(inventory_path, inventory)
        content_receipts[digest] = source
        content_formats[digest] = {"representation": item["google_representation"], "payload_sha256": item["uploaded_payload_sha256"]}

    async def organize_title(item, attempt, source):
        if not attempt or attempt.get("title_organized"):
            return
        # O nome técnico identifica a transferência; o estudante vê o título.
        # Depois de organizado uma vez, respeita renomeações manuais no Google.
        display_title = attempt.setdefault("display_title", source_display_title(item))
        save_journal()
        try:
            if source.title != display_title:
                updated = await client.sources.rename(notebook_id, source.id, display_title)
                if updated is not None:
                    source.title = updated.title
            attempt["title_organized"] = True
            save_journal()
            item["google_source_title"] = source.title
            atomic_json(inventory_path, inventory)
        except Exception as error:
            attempt["title_error_type"] = type(error).__name__
            save_journal()
            counts["title_update_pending"] += 1

    # Identifica conteúdos que já possuem um recibo válido e ainda existem.
    for item in list(inventory["resources"]) + list(known_resources):
        source = remote.get(item.get("google_source_id"))
        if (source and source.is_ready and item.get("uploaded_notebook_id") == notebook_id
                and item.get("google_upload_status") in {"processed", "processed-and-cited"}
                and item.get("uploaded_sha256")):
            content_receipts[item["uploaded_sha256"]] = source
            content_formats[item["uploaded_sha256"]] = {"representation": item.get("google_representation", "original"),
                "payload_sha256": item.get("uploaded_payload_sha256", item["uploaded_sha256"])}

    for item in inventory["resources"]:
        if item.get("moodle_removed"):
            result(item, "removed_from_moodle_preserved")
            continue
        relative = item.get("local_path")
        if not relative:
            result(item, "await_download")
            continue
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Arquivo fora da biblioteca do projeto.")
        if not _filesystem_path(path).is_file():
            result(item, "missing_file")
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            result(item, "local_only")
            continue
        digest = checksum(path)
        if digest != item.get("sha256"):
            result(item, "local_changed_after_collection")
            continue
        key = str(item["resource_id"]) + ":" + digest
        attempt = journal["attempts"].get(key)
        if attempt and attempt["status"] == "uploaded" and attempt.get("last_error_type") == "SourceProcessingError":
            attempt["status"] = "processing_failed"
        source_id = item.get("google_source_id")
        if attempt and attempt["status"] in {"intent", "uncertain"}:
            result(item, "uncertain_upload_review")
            break
        if digest in content_receipts and item.get("uploaded_sha256") != digest:
            receipt(item, digest, content_receipts[digest])
            result(item, "associated_identical_content")
            continue
        if adopt_existing and not item.get("uploaded_sha256") and not item.get("baseline_local_sha256"):
            # É referência local inicial; não afirma igualdade do arquivo remoto.
            source = remote.get(source_id) if source_id else None
            if source is None and not source_id:
                keys = {title_key(path.name.split("--", 1)[-1]), title_key(item["title"])}
                candidates = [candidate for candidate in remote.values() if title_key(candidate.title or "") in keys]
                if len(candidates) == 1:
                    source = candidates[0]
            if source and source.is_ready:
                item.update(google_source_id=source.id, google_source_title=source.title,
                            baseline_local_sha256=digest, baseline_notebook_id=notebook_id, baseline_source_id=source.id,
                            google_upload_status="existing-preserved", existing_content_hash_verified=False)
                source_id = source.id
                atomic_json(inventory_path, inventory)
        baseline = (item.get("baseline_notebook_id") == notebook_id
                    and item.get("baseline_source_id", source_id) == source_id and item.get("baseline_local_sha256"))
        if baseline and baseline == digest:
            source = remote.get(source_id)
            result(item, "existing_preserved" if source and source.is_ready else "remote_missing_or_not_ready_review")
            continue
        if source_id and (not item.get("uploaded_sha256") or item.get("uploaded_notebook_id") != notebook_id):
            if not baseline:
                result(item, "legacy_receipt_review")
                continue
        if (source_id and item.get("uploaded_sha256") == digest
                and item.get("uploaded_notebook_id") == notebook_id):
            source = remote.get(source_id)
            if source and source.is_ready:
                await organize_title(item, attempt, source)
                result(item, "current")
            else:
                result(item, "remote_missing_or_not_ready_review")
            continue
        # Após crash, um recibo retornado e persistido é evidência suficiente.
        # Um título coincidente ou source_id apenas de registro parcial não é.
        if attempt:
            if attempt["status"] == "processing_failed":
                if path.suffix.lower() != ".pdf" or os.name != "nt" or attempt.get("representation", "original") != "original":
                    result(item, "processing_failed_review")
                    continue
                try:
                    try:
                        prepared = prepare_ocr(root, path, course_id, item["resource_id"], digest)
                        representation, suffix = "ocr-text", " (texto reconhecido)"
                    except ValueError:
                        prepared = prepare_plan_image(root, path, course_id, item["resource_id"], digest)
                        representation, suffix = "pdf-image", " (imagem da planta)"
                    attempt.update(status="ocr_prepared", representation=representation, payload_path=prepared.relative_to(root).as_posix(),
                                   payload_sha256=checksum(prepared), failed_pdf_source_id=attempt.get("source_id"),
                                   display_title=source_display_title(item)[:176] + suffix)
                    attempt.pop("source_id", None)
                    save_journal()
                except Exception:
                    result(item, "processing_failed_review")
                    continue
            if attempt["status"] in {"uploaded", "ready"} and attempt.get("source_id"):
                source = remote.get(attempt["source_id"])
                if source is None:
                    result(item, "remote_missing_review")
                    continue
                try:
                    source = await client.sources.wait_until_ready(notebook_id, source.id, timeout=wait_timeout)
                except Exception as error:
                    attempt["last_error_type"] = type(error).__name__
                    if type(error).__name__ == "SourceProcessingError":
                        attempt["status"] = "processing_failed"
                    save_journal()
                    result(item, "processing_pending_or_failed")
                    if isinstance(error, TimeoutError) or type(error).__name__ in {"SourceProcessingError", "SourceTimeoutError"}:
                        continue
                    break
                attempt.update(status="ready", completed_at=timestamp())
                save_journal()
                receipt(item, digest, source, attempt)
                await organize_title(item, attempt, source)
                remote[source.id] = source
                result(item, "reconciled")
                continue
            if attempt["status"] not in {"not_sent", "rejected", "ocr_prepared"}:
                result(item, "uncertain_upload_review")
                break
        if digest in content_receipts:
            receipt(item, digest, content_receipts[digest])
            result(item, "associated_identical_content")
            continue
        if counts["uploaded"] + counts["uploaded_ocr"] + counts["uploaded_image"] >= max_uploads:
            result(item, "next_batch")
            continue
        if len(remote) >= source_limit:
            result(item, "source_limit_reached")
            break
        if not attempt and is_scanned_pdf(path):
            try:
                ocr_path = prepare_ocr(root, path, course_id, item["resource_id"], digest)
                attempt = {"status": "ocr_prepared", "representation": "ocr-text",
                           "payload_path": ocr_path.relative_to(root).as_posix(), "payload_sha256": checksum(ocr_path),
                           "display_title": source_display_title(item)[:176] + " (texto reconhecido)"}
                journal["attempts"][key] = attempt
                save_journal()
            except Exception:
                # O conector ainda pode aceitar o original quando a leitura
                # nativa não estiver disponível neste computador.
                attempt = None
        # Mesmo título sem recibo não comprova igualdade; evita duplicar legado.
        known_title = item.get("google_source_title") or path.name.split("--", 1)[-1]
        if any(source.title == known_title and source.id != source_id for source in remote.values()):
            result(item, "existing_title_review")
            continue
        stage_dir = root / "private" / "upload-staging"
        stage_dir.mkdir(parents=True, exist_ok=True)
        human = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", path.stem.split("--", 1)[-1])[:85]
        transformed = attempt and attempt.get("representation") in {"ocr-text", "pdf-image"}
        payload = (root / attempt["payload_path"]).resolve() if transformed else path
        if not payload.is_relative_to(root): raise ValueError("Cópia para envio fora da biblioteca.")
        payload_digest = checksum(payload)
        if transformed and payload_digest != attempt["payload_sha256"]:
            raise ValueError("A cópia preparada mudou; revisar antes de enviar.")
        staged = stage_dir / f"moodle-{course_id}-{item['resource_id']}-{digest[:12]}--{human}{payload.suffix}"
        shutil.copyfile(_filesystem_path(payload), staged)
        if checksum(staged) != payload_digest:
            raise ValueError("A cópia para envio mudou; coleta precisa ser repetida.")
        attempt = {**(attempt or {}), "status": "intent", "sha256": digest, "started_at": timestamp(),
                   "display_filename": staged.name,
                   "representation": attempt["representation"] if transformed else "original", "payload_sha256": payload_digest,
                   "display_title": attempt["display_title"] if transformed else source_display_title(item, updated=bool(source_id))}
        journal["attempts"][key] = attempt
        save_journal()  # Antes de qualquer mutação no Google.
        try:
            source = await client.sources.add_file(notebook_id, staged, wait=False)
        except Exception as error:
            commit = getattr(error, "commit_state", None)
            state = getattr(commit, "value", None)
            partial_id = getattr(error, "source_id", None)
            attempt.update(status=state if state in {"not_sent", "rejected"} and not partial_id else "uncertain",
                           last_error_type=type(error).__name__, source_id=partial_id,
                           stage=getattr(error, "stage", None))
            save_journal()
            result(item, "upload_failed_" + attempt["status"])
            break
        attempt.update(status="uploaded", source_id=source.id, bytes_confirmed_at=timestamp())
        save_journal()  # O processamento é uma segunda etapa, sem novo upload.
        remote[source.id] = source
        try:
            source = await client.sources.wait_until_ready(notebook_id, source.id, timeout=wait_timeout)
        except Exception as error:
            attempt["last_error_type"] = type(error).__name__
            if type(error).__name__ == "SourceProcessingError":
                attempt["status"] = "processing_failed"
            save_journal()
            result(item, "processing_pending_or_failed")
            if isinstance(error, TimeoutError) or type(error).__name__ in {"SourceProcessingError", "SourceTimeoutError"}:
                continue
            break
        attempt.update(status="ready", completed_at=timestamp())
        save_journal()
        receipt(item, digest, source, attempt)
        await organize_title(item, attempt, source)
        remote[source.id] = source
        result(item, {"ocr-text": "uploaded_ocr", "pdf-image": "uploaded_image"}.get(attempt.get("representation"), "uploaded"))
        if progress:
            progress(str(item["resource_id"]), dict(counts))
        print(f"Arquivo processado: {item['resource_id']}", flush=True)
        if pause:
            await asyncio.sleep(pause)

    final_remote = await client.sources.list(notebook_id, strict=True)
    return {"checked_at_utc": timestamp(), "course_id": course_id, "course_title": expected_title, "notebook_id": notebook_id,
            "live_remote_state_verified": True, "remote_source_count": len(final_remote),
            "summary": dict(counts), "items": results}
