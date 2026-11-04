import errno
import os
from pathlib import Path
import socket
import sys


assert os.getuid() != 0, "daemon must not run as root"
status = Path("/proc/self/status").read_text()
assert "CapEff:\t0000000000000000" in status
assert "NoNewPrivs:\t1" in status
for family in (socket.AF_INET, socket.AF_INET6):
    try:
        connection = socket.socket(family, socket.SOCK_STREAM)
    except OSError as error:
        assert error.errno in (errno.EAFNOSUPPORT, errno.EPERM), error
    else:
        connection.close()
        raise AssertionError("Internet sockets must be blocked")
try:
    os.open("/usr/ydotool-sandbox-probe", os.O_CREAT | os.O_WRONLY, 0o600)
except OSError as error:
    assert error.errno in (errno.EROFS, errno.EACCES), error
else:
    raise AssertionError("system filesystem must not be writable")
try:
    list(Path(sys.argv[2]).iterdir())
except PermissionError:
    pass
else:
    raise AssertionError("user home must not be accessible")
fd = os.open("/dev/uinput", os.O_WRONLY)
os.close(fd)
with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as local:
    local.connect(sys.argv[1])
    local.send(b"")
print("PASS: non-root, no capabilities, no privilege escalation, IPv4/IPv6 blocked, filesystem protected, uinput and local socket available")
