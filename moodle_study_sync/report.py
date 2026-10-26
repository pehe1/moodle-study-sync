"""Relatório legível, local e sem dados de acesso."""

from datetime import datetime
from html import escape


def write_status(path, report):
    labels = {"current": "Já estava atualizado", "uploaded": "Enviado e processado",
              "reconciled": "Envio anterior confirmado", "associated_identical_content": "Conteúdo idêntico associado",
              "next_batch": "Aguardando próximo lote", "removed_from_moodle_preserved": "Retirado do Moodle; cópia preservada",
              "existing_preserved": "Fonte anterior preservada; versão original não conferida",
              "local_only": "Guardado na pasta local; formato de laboratório",
              "uploaded_ocr": "Texto reconhecido enviado; PDF original preservado"}
    status = report.get("status")
    heading = "Tudo atualizado" if status == "ok" else "Coleta concluída" if status == "collection_ok" else "Precisa de atenção"
    date = datetime.fromisoformat(report.get("finished_at_utc", report["started_at_utc"])).astimezone().strftime("%d/%m/%Y às %H:%M")
    summary = report.get("summary", {})
    courses = report.get("courses", [])
    all_items = report.get("items", []) if not courses else [dict(item, title=row.get("name", "") + " — " + item["title"]) for row in courses for item in row.get("items", [])]
    rows = "".join("<tr><td>" + escape(item["title"]) + "</td><td>" +
                   escape(labels.get(item["action"], "Revisar: " + item["action"])) + "</td></tr>"
                   for item in all_items)
    notebooks = {}
    for course in courses:
        notebooks[course["notebook_id"]] = course
    course_links = "".join('<p><a href="https://notebook.google.com/notebook/' + escape(identifier, quote=True) + '">' + escape(course.get("name", "Matéria")) + '</a></p>' for identifier, course in notebooks.items())
    attention = ("<p>O progresso foi preservado. Se o acesso venceu, abra <b>Conectar-Google.cmd</b> na pasta do projeto. "
                 "O relatório técnico está em <b>last-sync.json</b>.</p>") if status == "attention_required" else ""
    schedule = ("Rotina diária às " + escape(report["scheduled_daily_at"]) +
                ". O computador deve estar ligado, conectado à internet e com sua sessão do Windows aberta. Se perder o horário, o Windows tentará executar depois.") if report.get("scheduled_daily_at") else "Agendamento ainda não instalado."
    document = f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Meus materiais de estudo</title><style>body{{font:17px/1.6 system-ui;max-width:960px;margin:48px auto;padding:0 24px;color:#223044;background:#f5f7fb}}h1{{margin-bottom:4px}}.card{{background:white;border-radius:16px;padding:24px;margin:24px 0}}td{{border-bottom:1px solid #e3e8f0;padding:12px 8px;text-align:left}}table{{width:100%;font-size:14px}}small{{color:#526174}}</style>
<h1>{heading}</h1><small>Última execução: {date}</small>
<div class="card"><b>{escape(report.get('course_title', 'Sua biblioteca de estudo'))}</b><p>{report.get('remote_source_count', '—')} fontes no Google · {summary.get('uploaded', 0)} novos envios nesta execução</p>
{course_links if notebooks else '<a href="https://notebook.google.com/notebook/' + escape(report.get('notebook_id', ''), quote=True) + '">Abrir notebook da matéria</a>'}{attention}</div>
<p>{schedule}</p>
<div class="card"><table><tr><th>Material</th><th>Situação</th></tr>{rows}</table></div></html>"""
    path.write_text(document, encoding="utf-8")
