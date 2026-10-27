"""Read-only lexical C naming checks. Results cover explicit naming, not C semantics."""
import argparse
import json
from pathlib import Path
import re


COMBINED = re.compile(r'^[A-Z][A-Za-z0-9]*(?:_(?:[A-Z][A-Za-z0-9]*|[0-9]+))+$')
ABBREVIATIONS = {'Voltage': 'Vol', 'Buffer': 'Buf', 'Data': 'Dat',
                 'State': 'Sta', 'Project': 'Pj', 'Module': 'Mod'}
KEYWORDS = {'void', 'char', 'short', 'int', 'long', 'float', 'double', 'signed', 'unsigned',
            'const', 'volatile', 'restrict', 'struct', 'union', 'enum', 'static', 'extern',
            'inline', 'typedef', 'register', '_Bool', '_Atomic'}


def mask_source(text):
    pattern = r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    text = re.sub(pattern, lambda m: ''.join('\n' if ch == '\n' else ' ' for ch in m.group()), text)
    return re.sub(r'(?m)^[ \t]*#(?:[^\n]*\\\n)*[^\n]*',
                  lambda m: ''.join('\n' if ch == '\n' else ' ' for ch in m.group()), text)


def matching(text, start, opening='(', closing=')'):
    level = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            level += 1
        elif text[index] == closing:
            level -= 1
            if level == 0:
                return index
    return None


def split_declarations(text, separator=','):
    result, start = [], 0
    depths = {'(': 0, '[': 0, '{': 0}
    close = {')': '(', ']': '[', '}': '{'}
    for index, char in enumerate(text):
        if char in depths:
            depths[char] += 1
        elif char in close:
            depths[close[char]] -= 1
        elif char == separator and not any(depths.values()):
            result.append((start, text[start:index]))
            start = index + 1
    result.append((start, text[start:]))
    return result


def declarator_name(declaration):
    callback = re.search(r'\(\s*\*\s*([A-Za-z_]\w*)\s*\)', declaration)
    if callback:
        return callback.group(1)
    value = declaration.split('=', 1)[0].split(':', 1)[0]
    value = re.sub(r'\[[^]]*\]', ' ', value)
    # A nested aggregate declaration's member is after its closing brace.
    if '}' in value:
        value = value.rsplit('}', 1)[1]
    names = re.findall(r'[A-Za-z_]\w*', value)
    if not names:
        return None
    if len(names) == 1 and names[0] not in KEYWORDS:
        return None  # An unnamed typedef parameter is legal in a prototype.
    candidates = [name for name in names if name not in KEYWORDS]
    if not candidates:
        return None
    if re.match(r'^\s*(struct|union|enum)\s+', value) and len(candidates) < 2:
        return None
    return candidates[-1]


def audit_project(project_root, vendor_roots=()):
    root = Path(project_root).resolve()
    vendors = [Path(p).resolve() for p in vendor_roots]
    result = {'scope': 'Lexical C/H parameter and structure naming only; compiler and semantic reviews remain required.',
              'findings': [], 'manual': [], 'suggestions': [],
              'summary': {'files': 0, 'functions': 0, 'structs': 0}}
    seen = set()

    def add(rule, path, text, offset, name, message):
        key = (rule, path.as_posix(), offset, name)
        if key not in seen:
            seen.add(key)
            result['findings'].append({'rule': rule, 'file': path.relative_to(root).as_posix(),
                                       'line': text[:offset].count('\n') + 1, 'name': name, 'message': message})

    for path in sorted(root.rglob('*')):
        if path.suffix.lower() not in {'.c', '.h'} or not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            result['manual'].append({'file': str(path), 'reason': 'Symlink or external source needs explicit scope'})
            continue
        if any(path.resolve().is_relative_to(vendor) for vendor in vendors):
            continue
        if any(part in {'.git', '__pycache__', 'node_modules'} for part in path.relative_to(root).parts):
            continue
        result['summary']['files'] += 1
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8-sig', errors='strict')
        except UnicodeError:
            result['manual'].append({'file': path.relative_to(root).as_posix(), 'reason': 'Cannot decode strict UTF-8'})
            continue
        if re.search(r'[\u3400-\u9fff]', text) and not raw.startswith(b'\xef\xbb\xbf'):
            add('EF03', path, text, 0, '', 'Chinese own C/H requires UTF-8 BOM')
        masked = mask_source(text)

        def check_name(name, offset, context):
            if not name:
                return
            if not COMBINED.fullmatch(name):
                add('N08', path, text, offset, name, context + ': use Pascal_Underscore')

        for token in re.finditer(r'\b[A-Za-z_]\w*\b', masked):
            name = token.group()
            fragments = re.findall(r'[A-Z]+(?=[A-Z][a-z]|\d|_|$)|[A-Z]?[a-z]+|\d+', name)
            for full, short in ABBREVIATIONS.items():
                if full in fragments:
                    add('N08', path, text, token.start(), name, f'Explicit abbreviation: {full} -> {short}')
            for full, short in {'Charge': 'Chg', 'Target': 'Tag'}.items():
                if full in fragments:
                    result['suggestions'].append({'file': path.relative_to(root).as_posix(),
                                                   'name': name, 'message': f'New names prefer {full} -> {short}'})

        # Normal declarations/definitions; macros, C++ and attribute-heavy syntax require target analysis.
        pattern = r'(?m)^[ \t]*(?P<prefix>(?:[A-Za-z_]\w*\s+|\*\s*)+?)(?P<name>[A-Za-z_]\w*)\s*\('
        for match in re.finditer(pattern, masked):
            if match.group('prefix').strip().split()[0] in {'return', 'if', 'while', 'for', 'switch'}:
                continue
            start = match.end() - 1
            end = matching(masked, start)
            if end is None:
                result['manual'].append({'file': path.relative_to(root).as_posix(), 'reason': 'Unbalanced function declaration'})
                continue
            tail = masked[end + 1:].lstrip()
            if not tail.startswith(('{', ';')):
                continue
            result['summary']['functions'] += 1
            for local_offset, parameter in split_declarations(masked[start + 1:end]):
                name = declarator_name(parameter)
                check_name(name, start + 1 + local_offset, 'parameter')
                callback = re.search(r'\(\s*\*\s*\w+\s*\)\s*\(', parameter)
                if callback:
                    callback_start = callback.end() - 1
                    callback_end = matching(parameter, callback_start)
                    if callback_end is not None:
                        for nested_offset, nested in split_declarations(parameter[callback_start + 1:callback_end]):
                            check_name(declarator_name(nested), start + 1 + local_offset + nested_offset, 'callback parameter')

        for match in re.finditer(r'\bstruct\s+(?:(?P<tag>[A-Za-z_]\w*)\s*)?(?P<open>\{)', masked):
            if match.group('tag'):
                check_name(match.group('tag'), match.start('tag'), 'structure tag')
            result['summary']['structs'] += 1
            brace = match.start('open')
            end = matching(masked, brace, '{', '}')
            if end is None:
                result['manual'].append({'file': path.relative_to(root).as_posix(), 'reason': 'Unbalanced structure definition'})
                continue
            body = masked[brace + 1:end]
            for offset, statement in split_declarations(body, ';'):
                for part_offset, declaration in split_declarations(statement):
                    # Subsequent comma declarators have no leading type.
                    name = declarator_name(declaration)
                    if name is None and part_offset and re.fullmatch(r'\s*\**\s*[A-Za-z_]\w*\s*', declaration):
                        name = re.findall(r'[A-Za-z_]\w*', declaration)[-1]
                    check_name(name, brace + 1 + offset + part_offset, 'structure member')
            # typedef alias or object immediately following the definition.
            suffix = re.match(r'\s*([A-Za-z_]\w*)\s*[;,]', masked[end + 1:])
            if suffix:
                check_name(suffix.group(1), end + 1 + suffix.start(1), 'structure alias/object')
        for match in re.finditer(r'\bstruct\s+([A-Za-z_]\w*)\s+\**\s*([A-Za-z_]\w*)\s*(?=[=;,\[])', masked):
            check_name(match.group(1), match.start(1), 'structure type')
            check_name(match.group(2), match.start(2), 'structure object')
        if re.search(r'\b(?:__attribute__|__declspec|class|template)\b', masked):
            result['manual'].append({'file': path.relative_to(root).as_posix(),
                                     'reason': 'Compiler extension or C++ syntax needs target-aware parsing'})
    if not result['summary']['files']:
        result['manual'].append({'reason': 'No own C/H files in scope; no clean-review claim'})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', required=True, type=Path)
    parser.add_argument('--vendor-root', action='append', type=Path, default=[])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit_project(args.project_root, args.vendor_root)
    value = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(value, encoding='utf-8')
    print(value, end='')
    return 1 if result['findings'] else 2 if result['manual'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
