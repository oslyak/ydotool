"""Verify release completeness and the explicit native-review requirement."""
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
    (po / 'LINGUAS').write_text('en\ndz\n')

    def check():
        return subprocess.run([sys.executable, str(po / 'check_catalogs.py'), '--strict', '--require-reviewed', 'dz'], capture_output=True, text=True)

    missing = check()
    assert missing.returncode != 0 and 'missing locale catalogs: dz' in missing.stderr
    # An existing translated catalog supplies fixture content, not a real dz translation.
    fixture = messages(ROOT / 'po/uk.po')
    headers = dict(line.split(': ', 1) for line in fixture.pop('').splitlines() if ': ' in line)
    headers.update({'Language': 'dz', 'X-Native-Review': 'pending'})
    write_po(po / 'dz.po', fixture, headers)
    pending = check()
    assert pending.returncode != 0 and 'native-language review must be approved' in pending.stderr
    headers['X-Native-Review'] = 'approved'
    write_po(po / 'dz.po', fixture, headers)
    approved = check()
    assert approved.returncode == 0, approved.stderr
    fixture.pop(next(iter(fixture)))
    write_po(po / 'dz.po', fixture, headers)
    incomplete = check()
    assert incomplete.returncode != 0 and 'msgid set differs' in incomplete.stderr
print('release gate: missing, unreviewed and incomplete catalogs rejected; approved fixture accepted')
