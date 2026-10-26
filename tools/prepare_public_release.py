"""Gera uma distribuição de fontes por lista permitida, sem dados de uso real."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT_FILES = {'.gitignore', 'LICENSE', 'README.md', 'THIRD_PARTY_NOTICES.md',
              'CONTRIBUTING.md', 'SECURITY.md', 'config.example.toml', 'sync.example.toml',
              'requirements-google.txt', 'requirements-moodle-dl.txt',
              'Meus-Estudos.cmd', 'Atualizar-agora.cmd', 'Conectar-Google.cmd'}


def public_files(root):
    root = Path(root).resolve()
    selected = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for folder, suffixes in [('moodle_study_sync', {'.py', '.html', '.css', '.js'}),
                             ('docs', {'.md'}), ('tools', {'.py', '.ps1'}),
                             ('third_party/licenses', {'.txt'})]:
        selected.extend(p for p in (root / folder).rglob('*') if p.is_file() and p.suffix in suffixes
                        and '__pycache__' not in p.parts and 'conflict' not in p.name.casefold())
    selected.extend((root / 'tests').glob('test_*.py'))
    selected = sorted(set(selected))
    for path in selected:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Arquivo fora do projeto na seleção pública.')
        text = path.read_text(encoding='utf-8-sig')
        patterns = [r'ya29\.[A-Za-z0-9_-]{20,}',
                    r'"(?:access_token|refresh_token|SAPISID|__Secure-1PSID)"\s*:\s*"[^"\s]{12,}"',
                    r'(?:wstoken|token)=[a-f0-9]{32}\b',
                    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
        if any(re.search(pattern, text) for pattern in patterns):
            raise ValueError('Possível segredo em ' + path.relative_to(root).as_posix())
    return selected


def build(root, output):
    root = Path(root).resolve()
    files = public_files(root)
    for required in ['README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'SECURITY.md']:
        if root / required not in files:
            raise ValueError('Falta o arquivo obrigatório: ' + required)
    manifest = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
        archive.writestr('release-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.root / 'private/public-release/moodle-study-sync-source.zip'
    manifest = build(args.root, output)
    print(json.dumps({'files': len(manifest), 'output': str(output.resolve()),
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
