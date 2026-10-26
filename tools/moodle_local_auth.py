"""Recebe a autorização pelo navegador local e salva somente no diretório privado.

Não registra o conteúdo das requisições nem imprime a chave. A página só
aceita formulários da própria origem, com cookie e nonce contra CSRF.
"""

import argparse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import requests


def valid_local_form(origin, expected_origin, supplied_nonce, expected_nonce, cookie_value):
    """Aceita origem opaca do navegador embutido somente com nonce correto.

    O nonce imprevisível é entregue no formulário local, nunca na URL. Não há
    CORS liberado: páginas de outra origem não conseguem ler esse formulário.
    Navegadores comuns também precisam apresentar o cookie correspondente.
    """
    if origin not in {expected_origin, "null"}:
        return False
    if not secrets.compare_digest(supplied_nonce, expected_nonce):
        return False
    return origin == "null" or secrets.compare_digest(cookie_value, expected_nonce)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--course-id", type=int, required=True)
    args = parser.parse_args()
    site = urlsplit(args.url)
    if site.scheme != "https" or not site.netloc or site.username or site.password or site.query:
        parser.error("Endereço Moodle inválido.")
    config_path = args.state_dir / "config.json"
    if config_path.exists():
        parser.error("Uma configuração já existe; nenhuma será sobrescrita.")
    args.state_dir.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_urlsafe(32)
    finished = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def reply(self, status, text, cookie=False):
            raw = ("<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
                   "<title>Conectar Moodle-DL</title><style>body{font:18px system-ui;"
                   "max-width:680px;margin:60px auto;padding:24px}input{width:100%;"
                   "padding:12px;box-sizing:border-box}button{padding:12px;margin-top:20px}"
                   "</style>" + text + "</html>").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
            if cookie:
                self.send_header("Set-Cookie", "moodle_local_auth=" + nonce + "; HttpOnly; SameSite=Strict; Path=/")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path != "/":
                return self.reply(404, "<h1>Página não encontrada</h1>")
            self.reply(200, "<h1>Conectar Moodle-DL</h1><p>A autorização será validada no Moodle e "
                       "guardada apenas na pasta privada deste computador, fora do OneDrive.</p>"
                       "<form method='post' action='/connect'><input type='hidden' name='nonce' value='" + nonce + "'>"
                       "<label for='token'>Autorização de acesso</label>"
                       "<input id='token' name='token' type='password' autocomplete='off' required>"
                       "<button type='submit'>Conectar Moodle-DL</button></form>", cookie=True)

        def do_POST(self):
            nonlocal finished
            origin = "http://127.0.0.1:" + str(self.server.server_port)
            if self.path != "/connect" or self.headers.get("Origin") not in {origin, "null"}:
                print(json.dumps({"local_form_rejected": "origin", "origin_received": self.headers.get("Origin"),
                                  "expected_origin": origin}), flush=True)
                return self.reply(403, "<h1>Solicitação recusada</h1>")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length < 4096:
                return self.reply(400, "<h1>Solicitação inválida</h1>")
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            supplied_cookie = cookies.get("moodle_local_auth")
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            if not valid_local_form(self.headers.get("Origin"), origin, form.get("nonce", [""])[0],
                                    nonce, supplied_cookie.value if supplied_cookie else ""):
                print(json.dumps({"local_form_rejected": "csrf", "cookie_present": bool(supplied_cookie),
                                  "form_nonce_matches": secrets.compare_digest(form.get("nonce", [""])[0], nonce)}), flush=True)
                return self.reply(403, "<h1>Solicitação recusada</h1>")
            token = form.get("token", [""])[0]
            if not re.fullmatch(r"[a-zA-Z0-9]{32}", token):
                return self.reply(400, "<h1>Autorização inválida</h1>")
            try:
                response = requests.post(args.url.rstrip("/") + "/webservice/rest/server.php", data={
                    "wstoken": token, "wsfunction": "core_webservice_get_site_info", "moodlewsrestformat": "json"
                }, timeout=25)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or "userid" not in data or data.get("exception"):
                    return self.reply(403, "<h1>A autorização não foi aceita pelo Moodle</h1>")
                config = {
                    "moodle_domain": site.netloc, "moodle_path": site.path.rstrip("/") + "/", "token": token,
                    "download_course_ids": [args.course_id], "download_submissions": False,
                    "download_forums": False, "download_quizzes": False, "download_lessons": False,
                    "download_workshops": False, "download_books": False, "download_databases": False,
                    "download_calendars": False, "download_descriptions": False,
                    "download_links_in_descriptions": False, "download_linked_files": False,
                    "download_also_with_cookie": False, "do_not_ask_to_save_userid_and_version": True,
                }
                # Criação exclusiva: falhas não sobrescrevem credenciais existentes.
                with config_path.open("x", encoding="utf-8") as destination:
                    json.dump(config, destination, ensure_ascii=False, indent=2)
                    destination.write("\n")
            except (requests.RequestException, ValueError, OSError):
                return self.reply(500, "<h1>A conexão não foi concluída</h1><p>A configuração existente foi preservada.</p>")
            self.reply(200, "<h1>Moodle-DL conectado</h1><p>A autorização foi validada e guardada fora do OneDrive. "
                       "O teste está limitado à matéria selecionada.</p>")
            print(json.dumps({"authorization_saved": True, "authenticated_api_verified": True}), flush=True)
            finished = True

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 1
    deadline = time.monotonic() + 600
    print(json.dumps({"local_auth_url": "http://127.0.0.1:" + str(server.server_port) + "/"}), flush=True)
    try:
        while not finished and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
