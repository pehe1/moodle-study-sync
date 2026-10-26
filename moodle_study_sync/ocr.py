"""Alternativa local para PDFs digitalizados recusados pelo Google."""

import json
import os
from pathlib import Path
import subprocess


def is_scanned_pdf(path):
    if Path(path).suffix.lower() != ".pdf" or os.name != "nt":
        return False
    try:
        from pypdf import PdfReader
        absolute = Path(path).resolve()
        access_path = "\\\\?\\" + str(absolute) if not str(absolute).startswith("\\\\?\\") else str(absolute)
        reader = PdfReader(access_path)
        return not reader.is_encrypted and 0 < len(reader.pages) <= 80 and all(not page.extract_text().strip() for page in reader.pages)
    except Exception:
        return False


def prepare_ocr(root, path, course_id, resource_id, digest):
    if os.name != "nt" or Path(path).suffix.lower() != ".pdf":
        raise ValueError("Leitura local disponível para PDFs no Windows.")
    folder = Path(root) / "data" / "derived"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"{course_id}-{resource_id}-{digest}.txt"
    if not output.exists():
        result = subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-File",
            str(Path(root) / "tools" / "Read-ScannedPdf.ps1"), "-InputPdf", str(path), "-OutputText", str(output)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=240, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not output.is_file():
            raise ValueError("Este PDF precisa de conferência manual.")
    text = output.read_text(encoding="utf-8")
    if len(text.strip()) < 350:
        raise ValueError("Texto reconhecido insuficiente.")
    return output


def prepare_plan_image(root, path, course_id, resource_id, digest):
    """Renderiza uma planta de uma página sem substituir o PDF original."""
    if os.name != "nt" or Path(path).suffix.lower() != ".pdf":
        raise ValueError("Renderização local disponível para PDFs no Windows.")
    folder = Path(root) / "data" / "derived"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"{course_id}-{resource_id}-{digest}.png"
    if not output.exists():
        temporary = output.with_suffix(".tmp.png")
        result = subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-File",
            str(Path(root) / "tools" / "Render-PlanPdf.ps1"), "-InputPdf", str(path), "-OutputImage", str(temporary)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not temporary.is_file():
            temporary.unlink(missing_ok=True)
            raise ValueError("Este PDF precisa de conferência manual.")
        if temporary.stat().st_size < 100 or temporary.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            temporary.unlink(missing_ok=True)
            raise ValueError("A imagem não foi preparada corretamente.")
        temporary.replace(output)
    return output
