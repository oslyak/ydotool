import ast
import json
import os
import pathlib
import subprocess
import tempfile

binary = pathlib.Path(__import__('sys').argv[1]).resolve()
available = subprocess.check_output(['locale', '-a'], text=True).splitlines()
active_locale = next((name for name in available if name.lower() not in ('c', 'posix', 'c.utf8', 'c.utf-8') and 'utf' in name.lower()), None)
assert active_locale, 'A non-C UTF-8 locale is required; install/generate en_US.UTF-8 for gettext tests'

with tempfile.TemporaryDirectory(prefix='ydotool-locale-') as tmp:
    po = pathlib.Path(tmp) / 'fixture.po'
    mo = pathlib.Path(tmp) / 'fr/LC_MESSAGES/ydotool.mo'
    mo.parent.mkdir(parents=True)
    pot = pathlib.Path('po/ydotool.pot').resolve().read_text(encoding='utf-8').splitlines()
    msgids = []
    for index, line in enumerate(pot):
        if not line.startswith('msgid '):
            continue
        value = ast.literal_eval(line[6:])
        cursor = index + 1
        while cursor < len(pot) and pot[cursor].startswith('"'):
            value += ast.literal_eval(pot[cursor])
            cursor += 1
        if 'Use environment variable YDOTOOL_SOCKET' in value or 'Unknown command: %s' in value:
            msgids.append(value)
    assert len(msgids) == 2
    help_id = next(value for value in msgids if 'Use environment variable' in value)
    error_id = next(value for value in msgids if 'Unknown command:' in value)
    translated_help = help_id.replace('Use environment variable YDOTOOL_SOCKET to specify daemon socket.', 'LOCALIZED SOCKET HELP')
    translated_error = error_id.replace('Unknown command:', 'COMMANDE INCONNUE:')
    header_text = 'Project-Id-Version: ydotool-test\nPO-Revision-Date: 2026-11-06 00:00+0000\nLast-Translator: test\nLanguage-Team: test\nLanguage: fr\nMIME-Version: 1.0\nContent-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\n'
    header = 'msgid ""\nmsgstr ' + json.dumps(header_text) + '\n\n'
    po.write_text(header + 'msgid ' + json.dumps(help_id) + '\nmsgstr ' + json.dumps(translated_help) + '\n\nmsgid ' + json.dumps(error_id) + '\nmsgstr ' + json.dumps(translated_error) + '\n', encoding='utf-8')
    subprocess.run(['msgfmt', '--check', '--check-format', '-o', str(mo), str(po)], check=True)
    env = os.environ | {'YDOTOOL_LOCALEDIR': tmp, 'LC_ALL': active_locale, 'LANGUAGE': 'fr'}
    help_text = subprocess.run([binary, '--help'], env=env, text=True, capture_output=True, check=True).stdout
    assert 'LOCALIZED SOCKET HELP' in help_text
    error = subprocess.run([binary, 'user-☃'], env=env, text=True, capture_output=True)
    assert error.returncode == 1 and 'COMMANDE INCONNUE: user-☃' in error.stderr
    env['LANGUAGE'] = 'zz'
    fallback = subprocess.run([binary, '--help'], env=env, text=True, capture_output=True, check=True).stdout
    assert 'Use environment variable YDOTOOL_SOCKET' in fallback
    for locale in ('C', 'POSIX'):
        env['LC_ALL'] = locale
        env['LANGUAGE'] = 'fr'
        c_locale = subprocess.run([binary, '--help'], env=env, text=True, capture_output=True, check=True).stdout
        assert 'Use environment variable YDOTOOL_SOCKET' in c_locale and 'LOCALIZED SOCKET HELP' not in c_locale
print('gettext lookup, fallback, and C locale behavior passed')

# Exercise the actual built catalogs through both executables and a private socket.
import socket
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'po'))
from catalogs import messages
catalogs_dir = binary.parent / 'locale'
with tempfile.TemporaryDirectory(prefix='ydotool-translated-help-') as tmp:
    socket_path = str(pathlib.Path(tmp) / 'socket')
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(socket_path)
        for path in sorted(pathlib.Path('po').glob('*.po')):
            translation = messages(path)
            env = os.environ | {'LC_ALL': active_locale, 'LANGUAGE': path.stem, 'YDOTOOL_LOCALEDIR': str(catalogs_dir), 'YDOTOOL_SOCKET': socket_path}
            for args in [[], ['type', '--help'], ['key', '--help'], ['click', '--help'], ['mousemove', '--help'], ['release-all', '--help']]:
                result = subprocess.run([binary, *(args or ['--help'])], env=env, capture_output=True, text=True, check=True)
                command = args[0] if args else 'ydotool'
                msgid = next(key for key in translation if key.startswith('Usage: ') and key.split('\n', 1)[0].split(' ', 2)[1] == command)
                assert translation[msgid] in result.stdout, (path.stem, command)
            daemon = subprocess.run([binary.with_name('ydotoold'), '--help'], env=env, capture_output=True, text=True, check=True)
            msgid = next(key for key in translation if key.startswith('Usage: ydotoold '))
            assert translation[msgid] in daemon.stdout, path.stem
print('all built locale catalogs: client, command and daemon help verified without real input')
