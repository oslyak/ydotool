#!/usr/bin/env python3
"""Validate ydotool PO catalogs; use --strict after all planned languages land."""
import argparse
import pathlib
import subprocess
import tempfile

from catalogs import messages, validate_translation

root = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--strict', action='store_true', help='require every LINGUAS locale catalog to be complete')
args = parser.parse_args()
pot = messages(root / 'po/ydotool.pot')
msgids = set(pot) - {''}
langs = (root / 'po/LINGUAS').read_text().split()
missing = []
for lang in langs:
    path = root / 'po' / f'{lang}.po'
    if not path.exists():
        missing.append(lang)
        continue
    catalog = messages(path)
    if set(catalog) - {''} != msgids:
        raise SystemExit(f'{path}: msgid set differs from POT')
    for msgid, msgstr in catalog.items():
        if not msgid or not msgstr:
            continue
        try:
            validate_translation(msgid, msgstr)
        except ValueError as error:
            raise SystemExit(f'{path}: {error}: {msgid!r}') from error
        if lang != 'en' and len(msgid.split()) >= 4 and msgid == msgstr:
            raise SystemExit(f'{path}: untranslated English prose')
    with tempfile.NamedTemporaryFile(suffix='.mo') as output:
        subprocess.run(['msgfmt', '--check', '--check-format', '-o', output.name, str(path)], check=True)
    if args.strict and any(key and not value for key, value in catalog.items()):
        raise SystemExit(f'{path}: untranslated entries remain')
if missing and args.strict:
    raise SystemExit('missing locale catalogs: ' + ', '.join(missing))
print(f'{len(msgids)} msgids checked; {len(langs)} planned locales; {len(missing)} catalogs pending')
