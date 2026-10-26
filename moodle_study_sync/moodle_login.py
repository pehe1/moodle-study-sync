"""Renova o acesso institucional em uma janela em que o usuário entra sozinho."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import unquote, urlencode, urlsplit

import requests

from .moodle import read_config
from .storage import atomic_json, private_home


def main():
    from playwright.sync_api import sync_playwright
    root = Path(__file__).resolve().parents[1]
    runtime = json.loads((root / "private" / "runtime.local.json").read_text(encoding="utf-8-sig"))
    os.environ["MOODLE_STUDY_SYNC_HOME"] = runtime["private_home"]
    config = read_config()
    base = "https://" + config["moodle_domain"] + config["moodle_path"].rstrip("/")
    passport = secrets.token_hex(16)
    callback_hash = hashlib.md5((base + passport).encode()).hexdigest()
    with sync_playwright() as browser:
        context = browser.chromium.launch_persistent_context(str(private_home() / "moodle-browser"),
                           channel="msedge", headless=False, viewport=None, no_viewport=True)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(base + "/my/courses.php")
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                location = urlsplit(page.url)
                if location.netloc == config["moodle_domain"] and location.path.startswith("/my/"):
                    break
                page.wait_for_timeout(1000)
            else: return 2
            query = urlencode({"service": "moodle_mobile_app", "passport": passport,
                               "urlscheme": "moodledl", "confirmed": "1"})
            page.goto(base + "/admin/tool/mobile/launch.php?" + query)
            link = page.locator("a[href*='://token=']").first
            link.wait_for(state="visible", timeout=30000)
            encoded = unquote(link.get_attribute("href").split("token=", 1)[1].split("&", 1)[0])
            parts = base64.b64decode(encoded).decode().split(":::")
            if len(parts) < 2 or not secrets.compare_digest(parts[0], callback_hash) or not re.fullmatch(r"[a-zA-Z0-9]{32}", parts[1]):
                return 2
            response = requests.post(base + "/webservice/rest/server.php", data={"wstoken": parts[1],
                 "wsfunction": "core_webservice_get_site_info", "moodlewsrestformat": "json"}, timeout=30)
            response.raise_for_status()
            if "userid" not in response.json(): return 2
            config["token"] = parts[1]
            config.pop("privatetoken", None)
            atomic_json(private_home() / "moodle-dl" / "config.json", config)
            return 0
        finally: context.close()


if __name__ == "__main__":
    try: result = main()
    except Exception: result = 2
    raise SystemExit(result)
