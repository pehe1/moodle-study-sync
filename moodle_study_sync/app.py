"""App local: interface de cadastro e controle, acessível somente neste computador."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from urllib.parse import urlsplit
import webbrowser

from .app_service import (app_state, refresh_catalog, read_json, add_course, toggle_group,
                          connect_google, sync_busy)
from .run import execute
from .storage import atomic_json, private_home


def valid_api_request(host, origin, supplied, expected, port):
    return (host == f"127.0.0.1:{port}" and origin in {None, "null", f"http://127.0.0.1:{port}"}
            and isinstance(supplied, str) and secrets.compare_digest(supplied, expected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runtime = read_json(root / "private" / "runtime.local.json", {})
    if runtime.get("private_home"):
        os.environ["MOODLE_STUDY_SYNC_HOME"] = runtime["private_home"]
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    app_file = private_home() / "app-server.json"
    previous = read_json(app_file, {})
    if previous.get("pid"):
        # Reutiliza apenas o servidor que responde ao segredo desta instalação.
        try:
            import requests
            check = requests.get(previous["url"].split("#")[0] + "api/health",
                                 headers={"X-Study-Token": previous["token"]}, timeout=2)
            if check.status_code == 200:
                if not args.no_open: webbrowser.open(previous["url"])
                return
        except Exception:
            pass
    token = secrets.token_urlsafe(32)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="study-app")
    job_lock = threading.Lock()
    job = {"running": False, "message": ""}
    web = Path(__file__).parent / "web"

    def start_job(action, payload):
        with job_lock:
            if job["running"] or sync_busy(root):
                raise ValueError("Já existe uma atualização em andamento. Aguarde a conclusão.")
            job.update(running=True, action=action, message="Preparando…", error=False)

        def work():
            try:
                if action == "sync":
                    report, code = execute(root)
                    message = "Tudo atualizado." if code == 0 else "A atualização precisa de atenção. Confira as matérias."
                    if code: raise RuntimeError(message)
                elif action == "refresh":
                    refresh_catalog(root)
                    message = "Lista de matérias e notebooks atualizada."
                elif action == "add": message = add_course(root, payload)["message"]
                elif action == "toggle": message = toggle_group(root, payload)["message"]
                elif action == "google": message = connect_google(root)["message"]
                elif action == "moodle":
                    process = subprocess.run([sys.executable, "-m", "moodle_study_sync.moodle_login"],
                        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1000,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                    if process.returncode: raise PermissionError("Conexão Moodle não concluída.")
                    refresh_catalog(root)
                    message = "Moodle conectado."
                else: raise ValueError("Ação não reconhecida.")
                with job_lock: job.update(running=False, message=message, error=False)
            except Exception as error:
                message = str(error)[:240] if isinstance(error, ValueError) else "Não foi possível concluir. Confira o acesso às contas e tente novamente."
                with job_lock: job.update(running=False, message=message, error=True)
        executor.submit(work)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused): pass

        def send(self, status, data, mime="application/json; charset=utf-8"):
            if not isinstance(data, bytes): data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            return valid_api_request(self.headers.get("Host"), self.headers.get("Origin"),
                       self.headers.get("X-Study-Token"), token, self.server.server_port)

        def do_GET(self):
            route = urlsplit(self.path).path
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return self.send(403, {"message": "Origem não permitida."})
            files = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/app.css": ("app.css", "text/css; charset=utf-8"),
                     "/app.js": ("app.js", "text/javascript; charset=utf-8")}
            if route in files:
                filename, mime = files[route]
                return self.send(200, (web / filename).read_bytes(), mime)
            if not self.authorized(): return self.send(403, {"message": "Abra o app pelo atalho Meus Estudos."})
            if route == "/api/health": return self.send(200, {"ok": True})
            if route == "/api/catalog": return self.send(200, read_json(root / "private" / "catalog.json", {"moodle": [], "notebooks": []}))
            if route == "/api/state":
                state = app_state(root)
                with job_lock: state["job"] = dict(job)
                return self.send(200, state)
            return self.send(404, {"message": "Página não encontrada."})

        def do_POST(self):
            if not self.authorized(): return self.send(403, {"message": "Solicitação não autorizada."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 32768 or self.headers.get_content_type() != "application/json":
                    return self.send(400, {"message": "Solicitação inválida."})
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict): raise ValueError("Dados inválidos.")
                action = {"/api/sync": "sync", "/api/refresh": "refresh", "/api/add": "add",
                          "/api/toggle": "toggle", "/api/connect-google": "google", "/api/connect-moodle": "moodle"}.get(self.path)
                if self.path == "/api/open-library":
                    folder = root / "data" / "materials"
                    folder.mkdir(parents=True, exist_ok=True)
                    os.startfile(folder)
                    return self.send(200, {"message": "Biblioteca aberta."})
                if not action: return self.send(404, {"message": "Ação não encontrada."})
                start_job(action, payload)
                return self.send(202, {"message": "Solicitação iniciada."})
            except (ValueError, json.JSONDecodeError) as error:
                return self.send(400, {"message": str(error)[:240]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}/#{token}"
    atomic_json(app_file, {"url": url, "token": token, "pid": os.getpid(), "port": server.server_port})
    if not args.no_open: webbrowser.open(url)
    try: server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        executor.shutdown(wait=False)


if __name__ == "__main__": main()
