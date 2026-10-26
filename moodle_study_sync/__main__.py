"""Execute: python -m moodle_study_sync --inventory ARQUIVO --output ARQUIVO."""

import argparse
from collections import Counter
import json
from pathlib import Path

from .planner import plan_sync


def main():
    parser = argparse.ArgumentParser(description="Preparar prévia local; não faz upload.")
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(root):
        parser.error("O relatório deve ficar dentro da pasta do projeto.")
    if output == args.inventory.resolve() or output.suffix.lower() != ".json":
        parser.error("Use um arquivo JSON diferente do inventário para a prévia.")
    with args.inventory.open(encoding="utf-8") as source:
        inventory = json.load(source)
    try:
        plan = plan_sync(inventory, root)
    except ValueError as error:
        parser.error(str(error))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(dict(Counter(item["action"] for item in plan["items"])), ensure_ascii=True))


if __name__ == "__main__":
    main()
