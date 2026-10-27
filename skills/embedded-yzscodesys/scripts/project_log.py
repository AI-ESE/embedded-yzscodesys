"""Append project version and prompt records without overwriting history.

Use during an authorized project's implementation, not during pre-approval intake.
Python 3.10+ standard library. One writer at a time.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path, PureWindowsPath


NAMES = ('版本记录.md', '提示词记录.md')


def _root(project_root):
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError('project root must be an existing directory')
    folder = root / 'Log'
    if folder.is_symlink() or folder.resolve() != folder or (folder.exists() and not folder.is_dir()):
        raise ValueError('Log must be an ordinary directory inside the project')
    for name in NAMES:
        path = folder / name
        if path.is_symlink() or path.resolve() != path or (path.exists() and not path.is_file()):
            raise ValueError('Log record must be an ordinary file: ' + name)
    return root


def _required(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' is required')
    return value.strip()


def initialize(project_root):
    root = _root(project_root)
    folder = root / 'Log'
    folder.mkdir(exist_ok=True)
    for name in NAMES:
        path = folder / name
        if not path.exists():
            with path.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write('# ' + path.stem + '\n')
    return {'ok': True, 'directory': str(folder), 'files': list(NAMES)}


def _append(project_root, filename, text):
    initialize(project_root)
    path = _root(project_root) / 'Log' / filename
    old = path.read_bytes()
    old.decode('utf-8-sig', errors='strict')  # Reject unknown encoding without rewriting it.
    newline = b'\r\n' if b'\r\n' in old else b'\n'
    addition = text.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8').replace(b'\n', newline)
    with path.open('ab') as handle:
        handle.write((newline * 2 if old else b'') + addition + newline)
    return {'ok': True, 'file': str(path), 'appended': True}


def append_version(project_root, version, date, files, changes):
    root = _root(project_root)
    version, date, changes = (_required(v, field) for v, field in
                              ((version, 'version'), (date, 'date'), (changes, 'changes')))
    if not isinstance(files, (list, tuple)) or not files:
        raise ValueError('files must contain the actual changed project paths')
    paths = []
    for value in files:
        value = _required(value, 'file').replace('\\', '/')
        path = Path(value)
        if path.is_absolute() or PureWindowsPath(value).drive or '..' in path.parts or '\n' in value or '\r' in value:
            raise ValueError('changed file references must be relative project paths')
        if not (root / path).resolve().is_relative_to(root):
            raise ValueError('changed file reference escapes the project')
        paths.append(value)
    text = f'版本号：{version}\n修改日期：{date}\n修改涉及文件：\n' + '\n'.join('- ' + p for p in paths)
    text += '\n修改内容或者功能：\n' + changes
    return _append(root, NAMES[0], text)


def append_prompt(project_root, prompt_time, prompt, result):
    prompt_time, prompt, result = (_required(v, field) for v, field in
                                    ((prompt_time, 'prompt_time'), (prompt, 'prompt'), (result, 'result')))
    return _append(project_root, NAMES[1], f'提示词时间：{prompt_time}\n精简提示词内容：\n{prompt}\n最终改善输出：\n{result}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('init', 'append-version', 'append-prompt'):
        item = sub.add_parser(command)
        item.add_argument('--project-root', required=True, type=Path)
        if command == 'append-version':
            item.add_argument('--version', required=True)
            item.add_argument('--date', default=None)
            item.add_argument('--files', required=True, nargs='+')
            item.add_argument('--changes', required=True)
        if command == 'append-prompt':
            item.add_argument('--prompt-time', default=None)
            item.add_argument('--prompt', required=True)
            item.add_argument('--result', required=True)
    args = parser.parse_args()
    try:
        now = datetime.now().astimezone()
        if args.command == 'init':
            result = initialize(args.project_root)
        elif args.command == 'append-version':
            result = append_version(args.project_root, args.version, args.date or now.date().isoformat(), args.files, args.changes)
        else:
            result = append_prompt(args.project_root, args.prompt_time or now.isoformat(timespec='seconds'), args.prompt, args.result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
