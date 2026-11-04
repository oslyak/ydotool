import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class AutoSetupTests(unittest.TestCase):
    def test_local_accounts_access_lifecycle_and_admin_disable(self):
        with tempfile.TemporaryDirectory(prefix="ydotool-auto-test-") as directory:
            root = Path(directory)
            (root / "passwd").write_text("root:x:0:0::/:/bin/bash\nworker:x:1002:1002::/home/worker:/bin/bash\nother:x:1003:1002::/home/other:/bin/bash\nservice:x:1004:1004::/:/usr/sbin/nologin\nnobody:x:65534:65534::/:/bin/bash\n")
            (root / "shells").write_text("/bin/bash\n")
            (root / "login.defs").write_text("UID_MIN 1000\nUID_MAX 60000\n")
            (root / "groups").write_text("operators-team:x:1002:\nservice:x:1004:\n")
            (root / "enabled").mkdir()
            (root / "uinput").touch()
            mock = root / "mock"
            mock.write_text('''#!/usr/bin/python3
import os
from pathlib import Path
import sys
root = Path(os.environ["FIXTURE"])
command = Path(sys.argv[0]).name
if command == "getent":
    for line in (root / "groups").read_text().splitlines():
        if line.split(":")[2] == sys.argv[2]:
            print(line)
            sys.exit(0)
    sys.exit(2)
args = sys.argv[1:]
with (root / "calls").open("a") as log:
    log.write(" ".join(args) + "\\n")
unit = args[-1]
link = root / "enabled" / unit
if args[0] == "is-enabled":
    if (root / ("masked-" + unit)).exists():
        print("masked")
        sys.exit(1)
    print("enabled" if link.exists() else "disabled")
    sys.exit(0 if link.exists() else 1)
if args[0] == "enable":
    link.touch()
if args[0] == "disable":
    link.unlink(missing_ok=True)
''')
            mock.chmod(0o755)
            for command in ("systemctl", "getent"):
                (root / command).symlink_to(mock)
            script = (ROOT / "packaging/auto-setup").read_text()
            for source, target in (("/var/lib/ydotool", "state"), ("/etc/passwd", "passwd"), ("/etc/shells", "shells"), ("/etc/login.defs", "login.defs"), ("/sys/class/misc/uinput", "uinput")):
                script = script.replace(source, str(root / target))
            helper = root / "helper"
            helper.write_text(script)
            def run(*args):
                result = subprocess.run(["sh", str(helper), *args], env={**os.environ, "FIXTURE": str(root), "PATH": str(root) + ":/usr/bin:/bin"}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return (root / "calls").read_text()
            unit = r"ydotoold@operators\x2dteam.service"
            calls = run("--install")
            self.assertEqual(calls.count("enable " + unit + "\n"), 1)
            self.assertIn("start " + unit, calls)
            self.assertNotIn("ydotoold@service", calls)
            (root / "enabled" / unit).unlink()
            (root / "calls").write_text("")
            calls = run("--install")
            self.assertNotIn("enable ", calls)
            self.assertNotIn("start " + unit, calls)
            with (root / "passwd").open("a") as file:
                file.write("new-person:x:1005:1005::/home/new-person:/bin/bash\n")
            with (root / "groups").open("a") as file:
                file.write("new-person:x:1005:\n")
            with (root / "passwd").open("a") as file:
                file.write("manual:x:1006:1006::/home/manual:/bin/bash\nmasked:x:1007:1007::/home/masked:/bin/bash\n")
            with (root / "groups").open("a") as file:
                file.write("manual:x:1006:\nmasked:x:1007:\n")
            (root / "enabled/ydotoold@manual.service").touch()
            (root / "masked-ydotoold@masked.service").touch()
            calls = run()
            self.assertNotIn("enable ydotoold@manual.service", calls)
            self.assertNotIn("enable ydotoold@masked.service", calls)
            self.assertNotIn("start ydotoold@masked.service", calls)
            new_unit = r"ydotoold@new\x2dperson.service"
            self.assertIn("enable " + new_unit, calls)
            self.assertIn("start " + new_unit, calls)
            (root / "passwd").write_text("root:x:0:0::/:/bin/bash\n")
            calls = run()
            self.assertIn("disable --now " + new_unit, calls)
            self.assertFalse((root / "enabled" / new_unit).exists())
            self.assertEqual(list((root / "state").glob("group-*")), [])
            self.assertTrue((root / "enabled/ydotoold@manual.service").exists())


if __name__ == "__main__":
    unittest.main()
