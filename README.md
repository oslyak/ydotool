# ydotool

Linux keyboard and mouse automation for Wayland, X11 and consoles, using `/dev/uinput`. Written in **C23 (GNU extensions)**. Maintained by PosBit as a fork of [ReimuNotMoe/ydotool](https://github.com/ReimuNotMoe/ydotool).

## Install

On Debian amd64, with the PosBit APT repository configured:

```sh
sudo apt update
sudo apt install ydotool
sudo usermod -aG ydotool "$USER"
```

Download a [Debian DEB for amd64](https://github.com/oslyak/ydotool/releases/latest/download/ydotool_amd64.deb), [Debian DEB for arm64](https://github.com/oslyak/ydotool/releases/latest/download/ydotool_arm64.deb), [Ubuntu 24.04 DEB](https://github.com/oslyak/ydotool/releases/latest/download/ydotool_ubuntu2404_amd64.deb), or [Fedora/openSUSE RPM](https://github.com/oslyak/ydotool/releases/latest). DEBs require glibc 2.38+ and systemd. Install the downloaded package:

```sh
sudo apt install ./ydotool_amd64.deb
# Fedora: sudo dnf install ./ydotool_fedora43_x86_64.rpm
# openSUSE: sudo zypper install --allow-unsigned-rpm ./ydotool_opensuse16_x86_64.rpm
sudo usermod -aG ydotool "$USER"
```

The kernel must provide the `uinput` module.

Log out and back in to apply group membership. The package automatically starts one `ydotoold.service` as the system user `ydotool`.

## Use

```sh
# Check the connection without generating input.
ydotool debug

# Type ASCII text using the US keyboard mapping.
ydotool type 'Hello world!'

# Move the pointer by -100 horizontally and +100 vertically.
ydotool mousemove -x -100 -y 100

# Right mouse click.
ydotool click 0xC1

# Press and release Ctrl+V.
ydotool key 29:1 47:1 47:0 29:0

# Release stuck virtual keys and mouse buttons.
ydotool release-all
```

For Unicode text, use an external clipboard tool and paste. The active keyboard layout affects `type`. Absolute pointer positioning is approximate under Wayland.

The default socket is `/run/ydotoold/socket`; set `YDOTOOL_SOCKET` to use another socket.

See `ydotool COMMAND --help` or `man ydotool` for options. Check the service with `systemctl status ydotoold.service` and the version with `ydotoold --version`.

Licensed under [GNU AGPLv3](LICENSE). Original author: ReimuNotMoe.
