import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve()
PACKAGE_DIRECTORY = "/run/ydotoold"
PACKAGE_SOCKET = PACKAGE_DIRECTORY + "/socket"


class SocketPathTests(unittest.TestCase):
    def test_shared_socket_discovery_and_explicit_override(self):
        for scenario in ("default", "empty", "explicit", "missing", "denied", "custom"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory(prefix="ydotool-paths-") as directory:
                directory = Path(directory)
                real = directory / ".ydotool_socket"
                log = directory / "paths"
                with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
                    receiver.bind(str(real))
                    env = {k:v for k,v in os.environ.items() if k != "YDOTOOL_SOCKET"}
                    env.update(XDG_RUNTIME_DIR=str(directory), TEST_PATH_LOG=str(log),
                        TEST_PACKAGE_SOCKET=PACKAGE_SOCKET, TEST_PACKAGE_DIRECTORY=PACKAGE_DIRECTORY,
                        TEST_REAL_DIRECTORY=str(directory), TEST_REAL_SOCKET=str(real))
                    expected = [PACKAGE_SOCKET]
                    expected_rc = 0
                    if scenario == "empty": env["YDOTOOL_SOCKET"] = ""
                    if scenario == "explicit":
                        env["YDOTOOL_SOCKET"] = "/run/ydotoold/socket"
                        expected = [PACKAGE_SOCKET]
                    if scenario == "missing":
                        env["TEST_PACKAGE_MISSING"] = "1"
                        expected = [PACKAGE_SOCKET, str(real)]
                    if scenario == "denied":
                        env["TEST_PACKAGE_DENIED"] = "1"
                        expected_rc = 2
                    if scenario == "custom":
                        custom = str(directory / "custom-socket")
                        env["YDOTOOL_SOCKET"] = custom
                        expected = [custom]
                        expected_rc = 2
                    result = subprocess.run([str(BINARY), "debug"], env=env, capture_output=True, timeout=3)
                    self.assertEqual(result.returncode, expected_rc, result.stderr)
                    self.assertEqual(log.read_text().splitlines(), expected)


if __name__ == "__main__": unittest.main()
