from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class InstallTests(unittest.TestCase):
    def test_init_installation_without_pkg_config(self):
        for kind in ('user', 'system', 'openrc', 'override'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix='ydotool-install-') as directory:
                directory = Path(directory)
                build = directory / 'build'
                stage = directory / 'stage'
                args = ['cmake', '-S', str(ROOT), '-B', str(build),
                        '-DBUILD_DOCS=OFF', '-DYDOTOOL_VERSION=install-test',
                        '-DCMAKE_INSTALL_PREFIX=/opt/ydotool', '-DCMAKE_INSTALL_LIBDIR=lib64',
                        '-DCMAKE_DISABLE_FIND_PACKAGE_PkgConfig=TRUE',
                        '-DSYSTEMD_USER_SERVICE=' + ('ON' if kind in ('user', 'override') else 'OFF'),
                        '-DSYSTEMD_SYSTEM_SERVICE=' + ('ON' if kind == 'system' else 'OFF'),
                        '-DOPENRC=' + ('ON' if kind == 'openrc' else 'OFF')]
                if kind == 'override':
                    args.append('-DSD_UNITDIR=/custom/units')
                for command in (args, ['cmake', '--build', str(build), '--parallel', '2'],
                                ['cmake', '--install', str(build)]):
                    result = subprocess.run(command, env={**os.environ, 'DESTDIR': str(stage)}, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((stage / 'opt/ydotool/bin/ydotool').is_file())
                self.assertTrue((stage / 'opt/ydotool/share/locale/en/LC_MESSAGES/ydotool.mo').is_file())
                if kind == 'openrc':
                    script = stage / 'opt/ydotool/etc/init.d/ydotoold'
                    self.assertTrue(os.access(script, os.X_OK))
                    text = script.read_text()
                    self.assertIn('command="/opt/ydotool/bin/ydotoold"', text)
                    self.assertIn('command_user="ydotool:ydotool"', text)
                    result = subprocess.run(['sh', '-n', str(script)], capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    relative = 'custom/units' if kind == 'override' else 'opt/ydotool/lib/systemd/' + kind
                    text = (stage / relative / 'ydotoold.service').read_text()
                    self.assertIn('ExecStart=/opt/ydotool/bin/ydotoold', text)
                    self.assertNotIn('ExecReload=', text)


if __name__ == '__main__':
    unittest.main()
