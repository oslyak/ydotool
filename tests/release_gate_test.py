"""Verify that releases require complete catalogs for every supported locale."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'po'))
from catalogs import messages, write_po

with tempfile.TemporaryDirectory(prefix='ydotool-release-gate-') as directory:
    po = Path(directory) / 'po'
    po.mkdir()
    for name in ['catalogs.py', 'check_catalogs.py', 'ydotool.pot', 'en.po']:
        shutil.copy2(ROOT / 'po' / name, po / name)
    (po / 'LINGUAS').write_text('en\nuk\n')

    def check():
        return subprocess.run([sys.executable, str(po / 'check_catalogs.py'), '--strict'], capture_output=True, text=True)

    missing = check()
    assert missing.returncode != 0 and 'missing locale catalogs: uk' in missing.stderr
    shutil.copy2(ROOT / 'po/uk.po', po / 'uk.po')
    complete = check()
    assert complete.returncode == 0, complete.stderr
    fixture = messages(po / 'uk.po')
    headers = dict(line.split(': ', 1) for line in fixture.pop('').splitlines() if ': ' in line)
    first = next(iter(fixture))
    original = fixture.pop(first)
    write_po(po / 'uk.po', fixture, headers)
    incomplete = check()
    assert incomplete.returncode != 0 and 'msgid set differs' in incomplete.stderr
    fixture[first] = ''
    write_po(po / 'uk.po', fixture, headers)
    empty = check()
    assert empty.returncode != 0 and 'untranslated entries remain' in empty.stderr
    fixture[first] = original
    write_po(po / 'uk.po', fixture, headers)
    assert check().returncode == 0
print('release gate: missing, incomplete and empty translations rejected; complete supported set accepted')
