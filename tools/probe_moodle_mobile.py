"""Consulta somente a configuração pública do serviço móvel, sem credenciais."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query:
        parser.error("Use o endereço HTTPS base do Moodle, sem credenciais ou parâmetros.")
    base = args.url.rstrip("/")
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "site": base,
        "authenticated": False,
        "method": "tool_mobile_get_public_config",
        "status": "inconclusive",
    }
    try:
        response = requests.post(
            base + "/lib/ajax/service.php",
            params={"info": "tool_mobile_get_public_config"},
            json=[{"index": 0, "methodname": "tool_mobile_get_public_config", "args": {}}],
            timeout=25,
        )
        result["http_status"] = response.status_code
        result["content_type"] = response.headers.get("Content-Type", "")
        response.raise_for_status()
        payload = response.json()
        entry = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(entry, dict):
            result["reason"] = "unexpected_response"
        elif entry.get("error") or entry.get("exception"):
            error = entry.get("exception", entry)
            if not isinstance(error, dict):
                error = entry
            result.update(status="public_api_error", error_code=error.get("errorcode", "unknown"))
            result["message"] = error.get("message", "")[:1000]
        else:
            data = entry.get("data", entry)
            # Somente campos públicos necessários ao diagnóstico; sem sessão.
            allowed = {"enablewebservices", "enablemobilewebservice", "typeoflogin", "launchurl", "httpswwwroot", "wwwroot"}
            settings = {key: value for key, value in data.items() if key in allowed}
            result.update(status="public_config_received", settings=settings)
    except (requests.RequestException, ValueError, TypeError) as error:
        result["reason"] = type(error).__name__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
