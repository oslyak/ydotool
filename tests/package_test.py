import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class PackageTests(unittest.TestCase):
    def run_hook(self, name, action, *, fail_modprobe=False):
        with tempfile.TemporaryDirectory(prefix="ydotool-package-test-") as directory:
            directory = Path(directory)
            log = directory / "calls"
            mock = directory / "mock"
            mock.write_text('''#!/usr/bin/python3
import os
from pathlib import Path
import sys
name = Path(sys.argv[0]).name
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(name + " " + " ".join(sys.argv[1:]) + "\\n")
if name == "modprobe" and os.environ.get("FAIL_MODPROBE"):
    sys.exit(1)
if name == "systemctl" and sys.argv[1] == "list-unit-files":
    print("ydotoold@operators.service enabled enabled")
''')
            mock.chmod(0o755)
            for command in ("systemctl", "systemd-sysusers", "modprobe", "udevadm"):
                (directory / command).symlink_to(mock)
            hook = directory / name
            runtime = directory / "systemd"
            runtime.mkdir()
            hook.write_text((ROOT / "packaging" / name).read_text().replace("/run/systemd/system", str(runtime)))
            result = subprocess.run(["/bin/sh", str(hook), action],
                env={**os.environ, "PATH": str(directory) + ":/usr/bin:/bin", "CALL_LOG": str(log),
                     "FAIL_MODPROBE": "1" if fail_modprobe else ""}, capture_output=True, text=True)
            return result, log.read_text() if log.exists() else ""

    def test_remove_stops_and_disables_instances(self):
        result, calls = self.run_hook("prerm", "remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("systemctl stop ydotoold@*.service", calls)
        self.assertIn("systemctl disable ydotoold@operators.service", calls)

    def test_upgrade_does_not_stop_instances_in_prerm(self):
        result, calls = self.run_hook("prerm", "upgrade")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, "")

    def test_remove_and_purge_reload_units(self):
        for action in ("remove", "purge"):
            result, calls = self.run_hook("postrm", action)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("systemctl daemon-reload", calls)

    def test_configure_survives_unavailable_modprobe(self):
        result, calls = self.run_hook("postinst", "configure", fail_modprobe=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("systemd-sysusers", calls)
        self.assertIn("systemctl daemon-reload", calls)
        self.assertIn("uinput", result.stderr)


if __name__ == "__main__":
    unittest.main()
