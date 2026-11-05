import pathlib
import re
import subprocess
import tempfile
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "po"))
from catalogs import literal_tokens, messages, printf_placeholders, write_po

root = pathlib.Path(__file__).resolve().parents[1]

pot_ids = set(messages(root / 'po/ydotool.pot')) - {''}
po_ids = set(messages(root / 'po/en.po')) - {''}
assert len(pot_ids) > 20 and len(pot_ids) == len(set(pot_ids))
assert pot_ids == po_ids
linguas = (root / 'po/LINGUAS').read_text().split()
assert len(linguas) == len(set(linguas)) and {'en', 'uk', 'th'} <= set(linguas)
entries = __import__('json').loads((root/'po/debian-installer.json').read_text())['entries']
assert len(entries) == 78
assert set(linguas) <= {entry['code'] for entry in entries if entry['code'] != 'C'}
assert {path.stem for path in (root / 'po').glob('*.po')} == set(linguas)
with tempfile.TemporaryDirectory(prefix='ydotool-po-') as tmp:
    fixture = pathlib.Path(tmp) / 'fixture.po'
    write_po(fixture, {'Usage: tool --help\nPath: /usr/bin/tool %s': 'Uso: tool --help\nRuta: /usr/bin/tool %s'}, {'Language': 'es', 'Content-Type': 'text/plain; charset=UTF-8'})
    assert messages(fixture)['Usage: tool --help\nPath: /usr/bin/tool %s'] == 'Uso: tool --help\nRuta: /usr/bin/tool %s'
    assert '--help' in literal_tokens('Usage: tool --help') and '/usr/bin/tool' in literal_tokens('/usr/bin/tool')
    assert printf_placeholders('%s %2$d') == printf_placeholders('%s %2$d')
    subprocess.run(['msgfmt', '--check', '--check-format', '-o', tmp+'/en.mo', str(root/'po/en.po')], check=True)
print(f'catalog foundation: {len(pot_ids)} msgids, {len(linguas)} planned locales')

from catalogs import validate_translation
validate_translation("See `/usr/include/linux/input-event-codes.h' for key codes (KEY_*).", "Kody (KEY_*) są w /usr/include/linux/input-event-codes.h")
try:
    validate_translation("See `/usr/include/linux/input-event-codes.h' for key codes (KEY_*).", "Kody (KEY_*) są w /usr/include/linux/wrong.h")
except ValueError:
    pass
else:
    raise AssertionError('Changed path accepted')
validate_translation('Supports ASCII only', '日本語はASCIIのみ対応')
try:
    validate_translation('Supports ASCII only', 'UTF-8のみ対応')
except ValueError:
    pass
else:
    raise AssertionError('Changed encoding accepted')
with tempfile.TemporaryDirectory(prefix='ydotool-po-layout-') as tmp:
    fixture = pathlib.Path(tmp) / 'no-blanks.po'
    fixture.write_text('msgid "one"\nmsgstr "uno"\nmsgid "two"\nmsgstr "dos"\n')
    assert messages(fixture) == {'one': 'uno', 'two': 'dos'}
    fixture.write_text('msgid "one"\nmsgstr "uno"\n\nmsgid "one"\nmsgstr "otro"\n')
    try:
        messages(fixture)
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate msgid accepted')

with tempfile.TemporaryDirectory(prefix='ydotool-source-messages-') as tmp:
    extracted = pathlib.Path(tmp) / 'source.pot'
    sources = sorted(root.glob('Client/*.c')) + sorted(root.glob('Daemon/*.c'))
    subprocess.run(['xgettext', '--language=C', '--keyword=_', '--from-code=UTF-8', '--output', str(extracted), *map(str, sources)], check=True)
    assert set(messages(extracted)) - {''} == pot_ids, 'gettext template differs from production source'
