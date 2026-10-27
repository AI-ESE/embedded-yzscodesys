"""Validate a portable skill and create a deterministic local ZIP; never install it."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import zipfile


MANIFEST = 'package-manifest.json'
SKIP_PARTS = {'__pycache__', '.git', 'node_modules', '.pytest_cache', '.test-output', 'out', 'build', 'dist'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and not any(part in SKIP_PARTS for part in p.relative_to(root).parts)
                  and p.suffix not in {'.pyc', '.pyo'})


def check_package(skill_dir, verify_manifest=True):
    root = Path(skill_dir).resolve()
    errors, historical = [], []
    entry = root / 'SKILL.md'
    name = root.name
    if not entry.is_file():
        return {'ok': False, 'errors': ['SKILL.md missing'], 'historical_external_links': []}
    content = entry.read_text(encoding='utf-8-sig')
    front = re.match(r'^---\n(.*?)\n---(?:\n|$)', content, re.S)
    if not front:
        errors.append('SKILL.md requires LF-separated YAML frontmatter')
    else:
        name_match = re.search(r'^name:\s*([a-z0-9-]+)\s*$', front.group(1), re.M)
        description = re.search(r'^description:\s*(.+)$', front.group(1), re.M)
        if not name_match or len(name_match.group(1)) > 64:
            errors.append('Invalid skill name')
        else:
            name = name_match.group(1)
            if name != root.name:
                errors.append('Folder name and skill name differ')
        if not description or len(description.group(1)) > 1024:
            errors.append('Missing or oversized description')
        if '[TODO:' in content:
            errors.append('Unfinished skill scaffold')
    files = package_files(root)
    for path in root.rglob('*'):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append('Symlink/junction or escaping path: ' + str(path.relative_to(root)))
    for path in files:
        relative = path.relative_to(root).as_posix()
        try:
            if path.suffix == '.json':
                json.loads(path.read_text(encoding='utf-8-sig'))
            elif path.suffix == '.py':
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=relative)
            elif path.suffix == '.md':
                text = path.read_text(encoding='utf-8-sig')
                for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', text):
                    target = match.group(1).strip().strip('<>')
                    if target.startswith('#'):
                        continue
                    if re.match(r'^/?[A-Za-z]:[/\\]', target):
                        if relative.startswith('references/library/references/'):
                            historical.append({'document': relative, 'target': target})
                        else:
                            errors.append(f'Active document has machine-specific link: {relative}: {target}')
                        continue
                    parsed = urlsplit(target)
                    if parsed.scheme:
                        if parsed.scheme in {'http', 'https', 'mailto'}:
                            continue
                        errors.append(f'Unsupported link scheme: {relative}: {target}')
                        continue
                    clean = re.sub(r':\d+(?::\d+)?$', '', unquote(parsed.path))
                    resolved = (path.parent / clean).resolve()
                    if not resolved.is_relative_to(root):
                        errors.append(f'Link escapes package: {relative}: {target}')
                    elif not resolved.is_file():
                        errors.append(f'Missing reference: {relative}: {target}')
        except (ValueError, SyntaxError, UnicodeError, OSError) as exc:
            errors.append(f'{relative}: {exc}')
    manifest_path = root / MANIFEST
    if verify_manifest and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            expected = {row['path']: row['sha256'] for row in manifest['files']}
            current = {p.relative_to(root).as_posix(): digest(p) for p in files if p != manifest_path}
            if expected != current:
                errors.append('Package content differs from package-manifest.json; rebuild before distribution')
        except (KeyError, ValueError, TypeError, OSError) as exc:
            errors.append('Invalid package manifest: ' + str(exc))
    return {'ok': not errors, 'skill_name': name, 'file_count': len(files),
            'errors': errors, 'historical_external_links': historical}


def pack_skill(skill_dir, output):
    root, output = Path(skill_dir).resolve(), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError('ZIP output must be outside the skill directory')
    if output.exists():
        raise FileExistsError(output)
    report = check_package(root, verify_manifest=False)
    if not report['ok']:
        raise ValueError('\n'.join(report['errors']))
    rows = [{'path': p.relative_to(root).as_posix(), 'sha256': digest(p), 'size': p.stat().st_size}
            for p in package_files(root) if p != root / MANIFEST]
    distribution_path = root / 'assets' / 'distribution.json'
    version = '1.0.0'
    if distribution_path.is_file():
        version = json.loads(distribution_path.read_text(encoding='utf-8'))['version']
        if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
            raise ValueError('Invalid distribution version')
    manifest = {'schema_version': 1, 'skill_name': report['skill_name'], 'version': version,
                'scope': 'Local skill bundle; historical references are not live validation.', 'files': rows}
    (root / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in package_files(root):
            info = zipfile.ZipInfo(root.name + '/' + path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return {'ok': True, 'archive': str(output), 'sha256': digest(output),
            'files': len(rows) + 1, 'historical_external_links': len(report['historical_external_links'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'pack'])
    parser.add_argument('--skill-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'check':
            result = check_package(args.skill_dir)
        else:
            if not args.output:
                parser.error('pack requires --output')
            result = pack_skill(args.skill_dir, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
