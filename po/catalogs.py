"""Small GNU PO helpers shared by ydotool catalog maintenance scripts."""
import ast
import collections
import pathlib
import re


def messages(path):
    """Read GNU PO entries, including files without blank entry separators."""
    result, current, field = {}, {}, None

    def finish():
        if 'msgid' in current:
            key = current['msgid']
            if key in result:
                raise ValueError(f'{path}: duplicate msgid: {key!r}')
            result[key] = current.get('msgstr', '')
        current.clear()

    for line in pathlib.Path(path).read_text(encoding='utf-8').splitlines() + ['']:
        match = re.match(r'^(msgid|msgstr(?:\[\d+\])?|msgctxt) (.*)$', line)
        if match:
            name = match.group(1)
            if name == 'msgid' and 'msgid' in current:
                finish()
            field = name
            current.setdefault(field, '')
            current[field] += ast.literal_eval(match.group(2))
        elif line.startswith('"') and field:
            current[field] += ast.literal_eval(line)
        elif not line.strip() and current:
            finish()
            field = None
    return result


def literal_tokens(text):
    """Tokens whose spelling carries CLI, path, or machine-facing meaning."""
    tokens = set(re.findall(r'(?<![A-Za-z0-9_])(?:--?[A-Za-z][\w-]*|/[A-Za-z0-9_./*+-]+|[A-Z][A-Z0-9_]+|[A-Za-z][\w-]*\(\))', text))
    for token in ['ydotool', 'ydotoold', 'xinput', 'uinput', 'ioctl', 'stdin', 'release-all', 'CTRL-C', 'UTF-8', 'Dustin Van Tate Testa', 'Elliot Wolk', 'tofik']:
        if token in text:
            tokens.add(token)
    if 'UTF-8' in text:
        tokens.discard('UTF')
    tokens.update(re.findall(r'0x[0-9A-Fa-f]+', text))
    return tokens


def printf_placeholders(text):
    return collections.Counter(re.findall(r"%(?:\d+\$)?[-+#0 'I]*(?:\*|\d+)?(?:\.(?:\*|\d+))?(?:hh|h|ll|l|j|z|t|L)?[diouxXfFeEgGaAcspn%]", text))


def command_syntax(text):
    return [line.split(': ', 1)[1] for line in text.splitlines() if line.startswith('Usage: ')]


def validate_translation(msgid, msgstr):
    if not msgstr.strip():
        raise ValueError('empty translation')
    if not literal_tokens(msgid).issubset(literal_tokens(msgstr)):
        raise ValueError('literal command/flag/path changed')
    if printf_placeholders(msgid) != printf_placeholders(msgstr):
        raise ValueError('printf placeholders changed')
    for syntax in command_syntax(msgid):
        if syntax not in msgstr.splitlines()[0]:
            raise ValueError('usage command syntax changed')
    if msgid.endswith('\n') != msgstr.endswith('\n'):
        raise ValueError('trailing newline changed')


def write_po(path, catalog, headers):
    """Write a deterministic UTF-8 PO file from a mapping and header mapping."""
    import json
    header = ''.join(f'{key}: {value}\n' for key, value in headers.items())
    lines = ['msgid ""', 'msgstr ' + json.dumps(header, ensure_ascii=False), '']
    for msgid, msgstr in catalog.items():
        if printf_placeholders(msgid):
            lines.append('#, c-format')
        lines += ['msgid ' + json.dumps(msgid, ensure_ascii=False), 'msgstr ' + json.dumps(msgstr, ensure_ascii=False), '']
    pathlib.Path(path).write_text('\n'.join(lines), encoding='utf-8')
