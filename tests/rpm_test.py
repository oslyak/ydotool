import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / 'packaging/rpm/ydotool.spec'


class RpmTests(unittest.TestCase):
    def run_hook(self, section, count, *, systemd=True):
        with tempfile.TemporaryDirectory(prefix='ydotool-rpm-test-') as directory:
            directory = Path(directory)
            manager = directory / 'systemd'
            if systemd:
                manager.mkdir()
            device = directory / 'uinput'
            log = directory / 'calls'
            mock = directory / 'mock'
            mock.write_text('''#!/usr/bin/python3
import os
from pathlib import Path
import sys
name = Path(sys.argv[0]).name
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(name + ' ' + ' '.join(sys.argv[1:]) + '\\n')
if name == 'modprobe':
    Path(os.environ['DEVICE']).touch()
''')
            mock.chmod(0o755)
            for name in ('systemd-sysusers', 'systemctl', 'modprobe', 'udevadm'):
                (directory / name).symlink_to(mock)
            body = SPEC.read_text().split('%' + section + '\n', 1)[1].split('\n%', 1)[0]
            body = body.replace('/run/systemd/system', str(manager)).replace('/sys/class/misc/uinput', str(device))
            hook = directory / 'hook'
            hook.write_text('set -eu\n' + body)
            result = subprocess.run(['sh', str(hook), str(count)], env={**os.environ, 'PATH': str(directory) + ':/usr/bin:/bin', 'CALL_LOG': str(log), 'DEVICE': str(device)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return log.read_text() if log.exists() else ''

    def test_install_prepares_device_before_distribution_service_macros(self):
        calls = self.run_hook('post', 1)
        self.assertLess(calls.index('modprobe uinput'), calls.index('udevadm settle'))
        self.assertNotIn('systemctl enable', calls)
        self.assertNotIn('modprobe', self.run_hook('post', 1, systemd=False))

    def test_distribution_policy_is_not_overridden(self):
        spec = SPEC.read_text()
        self.assertNotIn('systemctl enable', spec)
        self.assertNotIn('-DCMAKE_C_FLAGS="-O', spec)
        for macro in ('%systemd_post ', '%systemd_preun ', '%systemd_postun_with_restart ',
                      '%service_add_pre ', '%service_add_post ', '%service_del_preun ', '%service_del_postun '):
            self.assertIn(macro + 'ydotoold.service', spec)

    def test_license_and_version_follow_project_sources(self):
        spec = SPEC.read_text()
        self.assertIn('License:        AGPL-3.0-or-later', spec)
        self.assertIn('Version:        @VERSION@', spec)
        self.assertTrue((ROOT / 'LICENSE').read_text().lstrip().startswith('GNU AFFERO GENERAL PUBLIC LICENSE'))


if __name__ == '__main__':
    unittest.main()
