import os
import contextlib
import fcntl
import queue
import signal
import threading
from pathlib import Path
import socket
import subprocess
import struct
import sys
import tempfile
import unittest


BINARY = Path(sys.argv.pop(1)).resolve()


class InputTests(unittest.TestCase):
    @contextlib.contextmanager
    def receiver(self):
        with tempfile.TemporaryDirectory(prefix="ydotool-test-") as directory:
            path = str(Path(directory) / "socket")
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
                receiver.bind(path)
                events = []
                received = queue.Queue()
                def drain():
                    while True:
                        event = receiver.recv(4096)
                        if event == b"stop":
                            return
                        events.append(event)
                        received.put(event)
                thread = threading.Thread(target=drain)
                thread.start()
                try:
                    yield path, events, received
                finally:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as stopper:
                        stopper.sendto(b"stop", path)
                    thread.join()

    def run_client(self, args, data=None):
        with self.receiver() as (path, events, received):
            result = subprocess.run(
                [os.fsencode(BINARY), *args], input=data,
                env={**os.environ, "YDOTOOL_SOCKET": path},
                capture_output=True, timeout=3,
            )
        return result, events

    def test_release_all_help_does_not_emit_events(self):
        result, events = self.run_client([b"release-all", b"--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, [])

    def test_explicit_hold_and_release_all_recovery(self):
        with self.receiver() as (path, events, received):
            for args in ([b"key", b"-d", b"0", b"29:1"], [b"release-all"]):
                result = subprocess.run([os.fsencode(BINARY), *args],
                    env={**os.environ, "YDOTOOL_SOCKET": path}, capture_output=True, timeout=3)
                self.assertEqual(result.returncode, 0, result.stderr)
        keys = [struct.unpack("@llHHi", event)[3:] for event in events if struct.unpack("@llHHi", event)[2] == 1]
        self.assertEqual(keys[0], (29, 1))
        self.assertEqual([key for key in keys if key[1]], [(29, 1)])
        for code in (29, 42, 54, 56, 97, 100, 272):
            self.assertIn((code, 0), keys[1:])

    def test_utf8_in_later_argument_is_rejected_before_typing(self):
        for args in ([b"type", b"abc", "Ж".encode()], [b"type", b"abc\\x80"]):
            result, events = self.run_client(args)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(events, [])

    def test_invalid_delays_and_options_are_rejected(self):
        cases = [(command, option, value) for command, option in
                 ((b"key", b"-d"), (b"type", b"-d"), (b"type", b"-D"),
                  (b"type", b"-H"), (b"click", b"-D"))
                 for value in (b"-1", b"3000000", b"junk", b"99999999999999999999")]
        for command, option, value in cases:
            with self.subTest(command=command, option=option, value=value):
                result, events = self.run_client([command, option, value, b"a"])
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(events, [])
        result, events = self.run_client([b"key", b"--file", b"x"])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(events, [])

    def test_stdin_does_not_drop_ascii_bytes(self):
        result, events = self.run_client([b"stdin"], b"abc")
        self.assertEqual(result.returncode, 0, result.stderr)
        codes = [struct.unpack("@llHHi", event)[3] for event in events if struct.unpack("@llHHi", event)[2] == 1]
        self.assertEqual(codes, [30, 30, 48, 48, 46, 46])

    def test_escape_state_does_not_leak_between_arguments(self):
        result, events = self.run_client([b"type", bytes([92]), b"a"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(events), 4)

    def test_interrupted_client_releases_keys_and_holds_command_lock(self):
        for command in ([b"key", b"-d", b"60000", b"29:1", b"29:0"],
                        [b"type", b"-H", b"60000", b"A"]):
            for termination in (signal.SIGINT, signal.SIGTERM):
                with self.subTest(command=command, signal=termination):
                    with self.receiver() as (path, events, received):
                        process = subprocess.Popen([os.fsencode(BINARY), *command],
                            env={**os.environ, "YDOTOOL_SOCKET": path}, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                        try:
                            received.get(timeout=3)
                            with contextlib.ExitStack() as stack:
                                fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
                                stack.callback(os.close, fd)
                                with self.assertRaises(BlockingIOError):
                                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        finally:
                            process.send_signal(termination)
                            process.communicate(timeout=3)
                    pressed = set()
                    for event in events:
                        _, _, kind, code, value = struct.unpack("@llHHi", event)
                        if kind == 1:
                            if value:
                                pressed.add(code)
                            else:
                                pressed.discard(code)
                    self.assertEqual(pressed, set())
                    self.assertEqual(process.returncode, 128 + termination)

    def test_non_ascii_is_rejected_without_events(self):
        for value in range(128, 256):
            for command in (b"type", b"stdin"):
                with self.subTest(byte=value, command=command):
                    args = [command, b"-e", b"0", b"--", bytes([value])] if command == b"type" else [command]
                    result, events = self.run_client(args, bytes([value]) if command == b"stdin" else None)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(b"ASCII", result.stderr)
                    self.assertNotIn(b"runtime error", result.stderr)
                    self.assertEqual(events, [])

    def test_ascii_still_emits_key_events(self):
        for args, data in (([b"type", b"-d", b"0", b"-H", b"0", b"a"], None), ([b"stdin"], b"a")):
            with self.subTest(args=args):
                result, events = self.run_client(args, data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(events), 4)

    def test_dictation_paste_key_sequence(self):
        result, events = self.run_client([b"key", b"-d", b"0", b"29:1", b"47:1", b"47:0", b"29:0"])
        self.assertEqual(result.returncode, 0, result.stderr)
        decoded = [struct.unpack("@llHHi", event)[2:] for event in events]
        expected = []
        for code, value in ((29, 1), (47, 1), (47, 0), (29, 0)):
            expected.extend(((1, code, value), (0, 0, 0)))
        self.assertEqual(decoded, expected)

    def test_type_file_rejects_utf8(self):
        result, events = self.run_client([b"type", b"-f", b"-"], "Україна".encode())
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(b"ASCII", result.stderr)
        self.assertEqual(events, [])

    def test_escaped_non_ascii_is_rejected(self):
        for value in (b"\\x80", b"\\xff"):
            result, events = self.run_client([b"type", value])
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(b"ASCII", result.stderr)
            self.assertEqual(events, [])

    def test_incomplete_escape_stops_at_string_end(self):
        for value in (bytes([92]), b"\\x", b"\\xf"):
            with self.subTest(value=value):
                result, events = self.run_client([b"type", value])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(events, [])

    def test_empty_inputs_emit_nothing(self):
        for args, data in (([b"type", b""], None), ([b"stdin"], b"")):
            result, events = self.run_client(args, data)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
