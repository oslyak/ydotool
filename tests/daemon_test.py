import contextlib
import os
from pathlib import Path
import select
import socket
import struct
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve()
PRELOAD = Path(sys.argv.pop(1)).resolve()


class DaemonTests(unittest.TestCase):
    @contextlib.contextmanager
    def daemon(self):
        with tempfile.TemporaryDirectory(prefix="ydotool-daemon-test-") as directory:
            directory = Path(directory)
            path = str(directory / "socket")
            output = directory / "events"
            reader, writer = os.pipe()
            with (directory / "setup").open("w+b") as setup:
                process = subprocess.Popen([str(BINARY), "--socket-path=" + path,
                    "--socket-perm=0660", "--no-system-keys"],
                    env={**os.environ, "LD_PRELOAD": str(PRELOAD), "TEST_UINPUT": str(output),
                         "TEST_SETUP_FD": str(setup.fileno()), "TEST_NOTIFY_FD": str(writer), "DISPLAY": ""},
                    pass_fds=(writer, setup.fileno()), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                os.close(writer)
                try:
                    self.assertTrue(select.select([reader], [], [], 3)[0], "daemon did not create virtual device")
                    self.assertEqual(os.read(reader, 1), b"R")
                    setup.seek(0)
                    registrations = list(struct.iter_unpack("@QQ", setup.read()))
                    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                        client.connect(path)
                        yield client, output, reader, registrations, Path(path)
                finally:
                    process.terminate()
                    process.communicate(timeout=3)
                    os.close(reader)

    def test_restricted_daemon_registers_mouse_and_omits_system_keys(self):
        with self.daemon() as (client, output, reader, registrations, path):
            self.assertEqual(path.stat().st_mode & 0o777, 0o660)
            # UI_SET_EVBIT=0x40045564 and UI_SET_KEYBIT=0x40045565 on Linux.
            evbits = [value for request, value in registrations if request == 0x40045564]
            keys = [value for request, value in registrations if request == 0x40045565]
            self.assertIn(2, evbits)  # EV_REL
            self.assertIn(0x110, keys)  # BTN_LEFT
            for key in (99, 116, 142, 205, 356, 408):
                self.assertNotIn(key, keys)

    def test_invalid_and_system_events_are_not_forwarded(self):
        with self.daemon() as (client, output, reader, registrations, path):
            event = lambda kind, code, value: struct.pack("@llHHi", 0, 0, kind, code, value)
            client.send(event(1, 116, 1))
            client.send(event(1, 99, 1))
            client.send(event(1, 30, 1) + b"oversized")
            client.send(b"short")
            accepted = event(2, 0, 10)
            client.send(accepted)
            self.assertTrue(select.select([reader], [], [], 3)[0], "accepted event not forwarded")
            self.assertEqual(os.read(reader, 1), b"E")
            self.assertEqual(output.read_bytes(), accepted)


if __name__ == "__main__":
    unittest.main()
