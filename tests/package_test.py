import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class PackageTests(unittest.TestCase):
    def run_hook(self, name, action, *, fail_modprobe=False, shadow_layout=None, old_version=None, no_enabled=False, no_systemd=False, legacy=False, admin_disabled=False):
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
if name == "dpkg-query":
    print(os.environ["TEST_PACKAGE_VERSION"])
if name == "modprobe" and os.environ.get("FAIL_MODPROBE"):
    sys.exit(1)
if name == "deb-systemd-helper":
    if "was-enabled" in sys.argv and os.environ.get("ADMIN_DISABLED"): sys.exit(1)
    if "purge" in sys.argv:
        Path(os.environ["UNIT_LINK"]).unlink(missing_ok=True)
''')
            mock.chmod(0o755)
            for command in ("systemctl", "systemd-sysusers", "modprobe", "udevadm", "dpkg-query", "deb-systemd-helper", "deb-systemd-invoke"):
                (directory / command).symlink_to(mock)
            hook = directory / name
            runtime = directory / "systemd"
            if not no_systemd: runtime.mkdir()
            canonical = directory / "usr/bin"
            local = directory / "usr/local/bin"
            canonical.mkdir(parents=True)
            local.mkdir(parents=True)
            if shadow_layout:
                for tool in ("ydotool", "ydotoold"):
                    (canonical / tool).write_text("packaged " + tool)
                    shadow = local / tool
                    if shadow_layout == "link":
                        shadow.symlink_to(canonical / tool)
                    elif shadow_layout == "copy":
                        shadow.write_bytes((canonical / tool).read_bytes())
                    elif shadow_layout == "known":
                        shadow.write_text("known local binary")
                    elif shadow_layout == "other-link":
                        alternate = directory / (tool + "-custom")
                        alternate.write_text("custom binary")
                        shadow.symlink_to(alternate)
                    else:
                        shadow.write_text("custom binary")
            script = (ROOT / "packaging" / name).read_text()
            script = script.replace("/var/lib/ydotool", str(directory / "state"))
            script = script.replace("/run/systemd/system", str(runtime))
            script = script.replace("/etc/systemd/system", str(directory / "etc/systemd/system"))
            units = directory / "etc/systemd/system/multi-user.target.wants"
            units.mkdir(parents=True)
            if not no_enabled:
                (units / "ydotoold.service").symlink_to("/usr/lib/systemd/system/ydotoold.service")
            if legacy:
                state = directory / "state"
                state.mkdir()
                (state / "units-initialized").touch()
                (units / "ydotoold@operators.service").symlink_to("/usr/lib/systemd/system/ydotoold@.service")
                (units / "ydotool-autosetup.path").symlink_to("/usr/lib/systemd/system/ydotool-autosetup.path")
                (units / "ydotoold@custom.service").symlink_to("/etc/systemd/system/custom.service")
            device = directory / "uinput"
            device.touch()
            script = script.replace("/sys/class/misc/uinput", str(device))
            script = script.replace("/usr/local/bin/", str(local) + "/")
            script = script.replace("/usr/bin/", str(canonical) + "/")
            hook.write_text(script)
            result = subprocess.run(["/bin/sh", str(hook), action, *([old_version] if old_version is not None else [])],
                env={**os.environ, "PATH": str(directory) + ":/usr/bin:/bin", "CALL_LOG": str(log), "UNIT_LINK": str(units / "ydotoold.service"),
                     "ADMIN_DISABLED": "1" if admin_disabled else "",
                     "FAIL_MODPROBE": "1" if fail_modprobe else "",
                     "TEST_NO_ENABLED": "1" if no_enabled else "",
                     "TEST_PACKAGE_VERSION": (ROOT / "VERSION").read_text().strip() + "+upstream.708e96f"}, capture_output=True, text=True)
            self.enabled_links = list(units.iterdir())
            self.remaining_shadows = [tool for tool in ("ydotool", "ydotoold") if (local / tool).exists() or (local / tool).is_symlink()]
            return result, log.read_text() if log.exists() else ""

    def test_configure_preserves_all_administrator_local_overrides(self):
        for layout in ("link", "copy", "known", "unknown", "other-link"):
            with self.subTest(layout=layout):
                result, calls = self.run_hook("postinst", "configure", shadow_layout=layout)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.remaining_shadows, ["ydotool", "ydotoold"])
                self.assertIn("local override", result.stderr)

    def test_upgrade_migrates_only_package_owned_legacy_instances(self):
        result, calls = self.run_hook("postinst", "configure", old_version="1.0.7+upstream.708e96f", legacy=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deb-systemd-invoke stop ydotool-autosetup.path ydotool-autosetup.service", calls)
        self.assertIn("deb-systemd-invoke stop ydotoold@operators.service", calls)
        self.assertNotIn("deb-systemd-invoke stop ydotoold@custom.service", calls)
        self.assertEqual({p.name for p in self.enabled_links}, {"ydotoold.service", "ydotoold@custom.service"})

    def test_hooks_work_without_a_running_systemd_manager(self):
        for hook, action in (("postinst", "configure"), ("prerm", "remove"), ("postrm", "purge")):
            result, calls = self.run_hook(hook, action, no_systemd=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("systemctl", calls)
            self.assertNotIn("find:", result.stderr)

    def test_fresh_install_without_enabled_instances_configures_successfully(self):
        result, calls = self.run_hook("postinst", "configure", no_enabled=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deb-systemd-helper enable ydotoold.service", calls)
        self.assertIn("deb-systemd-invoke start ydotoold.service", calls)
        self.assertNotIn("systemctl start ydotoold@", calls)

    def test_reinstall_starts_enabled_instances_without_restarting_active_ones(self):
        current = (ROOT / "VERSION").read_text().strip() + "+upstream.708e96f"
        result, calls = self.run_hook("postinst", "configure", old_version=current)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deb-systemd-invoke start ydotoold.service", calls)
        self.assertNotIn("deb-systemd-invoke restart", calls)
        result, calls = self.run_hook("postinst", "configure", old_version="1.0.5+upstream.708e96f")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deb-systemd-invoke restart ydotoold.service", calls)

    def test_configure_preserves_administrator_disable_and_does_not_add_users(self):
        result, calls = self.run_hook("postinst", "configure", admin_disabled=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deb-systemd-helper update-state ydotoold.service", calls)
        self.assertNotIn("deb-systemd-helper enable", calls)
        self.assertNotIn("usermod", calls)
        self.assertFalse(any(line.startswith("m ") for line in (ROOT / "packaging/ydotool.sysusers").read_text().splitlines()))

    def test_remove_preserves_configuration_and_purge_cleans_package_links(self):
        result, calls = self.run_hook("postrm", "remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.enabled_links), 1)
        result, calls = self.run_hook("postrm", "purge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.enabled_links, [])

    def test_remove_stops_instances_but_preserves_enablement(self):
        result, calls = self.run_hook("prerm", "remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deb-systemd-invoke stop ydotoold.service", calls)
        self.assertNotIn("systemctl disable", calls)

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
