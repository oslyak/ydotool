import argparse
import os
from pathlib import Path
import subprocess


parser = argparse.ArgumentParser(description="Run the packaged sandbox policy against an installed uinput device and daemon")
parser.add_argument("--group", required=True)
parser.add_argument("--home", required=True)
parser.add_argument("--socket", required=True)
args = parser.parse_args()
if os.geteuid() != 0:
    parser.error("run as root to create the transient system service")
root = Path(__file__).resolve().parent.parent
command = ["systemd-run", "--quiet", "--wait", "--pipe", "--collect"]
section = ""
for line in (root / "packaging/ydotoold@.service").read_text().splitlines():
    if line.startswith("["):
        section = line
    elif section == "[Service]" and "=" in line:
        key, value = line.split("=", 1)
        if key not in ("ExecStart", "Restart", "RestartSec", "RuntimeDirectory", "RuntimeDirectoryMode"):
            command.append("--property=" + line.replace("%i", args.group))
subprocess.run([*command, "/usr/bin/python3", "-c", (root / "tests/sandbox_probe.py").read_text(), args.socket, args.home], check=True)
