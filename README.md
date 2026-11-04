# ydotool — PosBit fork

Linux command-line keyboard and mouse automation through `/dev/uinput`, maintained as a fork of [ReimuNotMoe/ydotool](https://github.com/ReimuNotMoe/ydotool).

The client sends input events to a persistent `ydotoold` daemon, which holds a virtual input device. This works with Wayland, X11 and Linux consoles; it does not depend on an X server.

## This fork

Based on upstream commit `708e96f`, this fork adds input validation, checked event delivery, client command serialization, recovery for interrupted input and Debian packaging with a restricted system service.

The project is built as **C11** with compiler extensions enabled and uses Linux and POSIX APIs; see [CMakeLists.txt](CMakeLists.txt).

The release version is recorded in [VERSION](VERSION). Debian versions append the pinned upstream revision, for example `1.0.8+upstream.708e96f`.

## Install on Debian

With the signed PosBit APT repository already configured:

```sh
sudo apt update
sudo apt install ydotool
```

Alternatively, install a downloaded DEB using `sudo apt install ./path/to/ydotool.deb`.

The package creates and starts **one** `ydotoold.service` as the system user `ydotool`. Add each authorized user explicitly:

```sh
sudo usermod -aG ydotool "$USER"
```

Log out and back in so desktop applications receive the new group membership. The package does not add users automatically.

Check the installation after logging back in:

```sh
systemctl status ydotoold.service
ydotool debug
```

`debug` checks the client connection without generating input. The daemon reports its build version with `ydotoold --version`.

### Access and service restrictions

The socket is `/run/ydotoold/socket`, owned by `ydotool:ydotool` with mode `0660`, inside a directory with mode `0750`. Only root and authorized group members can connect.

The packaged daemon runs without root privileges or capabilities. Its separate `ydotool-uinput` group grants access to `/dev/uinput`; desktop users do not need that group. The service blocks network access, protects system files and home directories, and disables SysRq and power/sleep/restart keys through `--no-system-keys`. Mouse input remains enabled.

Membership in `ydotool` grants host input injection, not access limited to one application or login session. Add only trusted users. The service restrictions do not prevent clients from sending ordinary desktop shortcuts.

Updates preserve administrator service disablement. A same-version reinstall starts an enabled service without restarting an already running daemon; an upgrade restarts it to load the new binary.

## Commands and examples

Commands inject input into the current desktop or console. Check each command's options with `ydotool COMMAND --help`.

```sh
# Close the focused window: Alt+F4.
ydotool key 56:1 62:1 62:0 56:0

# Move the pointer by -100 horizontally and +100 vertically.
ydotool mousemove -x -100 -y 100

# Right mouse click.
ydotool click 0xC1

# Type ASCII text using the US keyboard mapping.
ydotool type 'Hello world!'

# Release virtual keyboard and mouse buttons after an interrupted client.
ydotool release-all
```

`key` accepts Linux keycodes; see `/usr/include/linux/input-event-codes.h`. `click` accepts button codes and press/release flags, documented in `man ydotool`. `stdin` translates terminal input into key events.

### Text and keyboard layouts

`type` uses a US keyboard mapping and rejects non-ASCII bytes, including UTF-8 text. The active desktop keyboard layout affects the resulting characters. For Ukrainian or other Unicode text, use an external clipboard tool and paste with a key combination; ydotool does not manage the clipboard.

Command-line text is validated before typing. File input is streamed, so valid text may already have been typed before a later invalid byte is rejected.

### Pointer coordinates

`mousemove` sends relative movements. Its `--absolute` option approximates an absolute position using relative events; pointer acceleration and compositor behavior can affect the result. It does not guarantee exact screen coordinates under Wayland.

### Interrupted commands

Cooperating clients serialize complete commands through a lock on the socket directory. Clients attempt to release their held keys on SIGINT, SIGTERM and send failures. SIGKILL cannot run cleanup; use `ydotool release-all` to recover. Key-down-only commands intentionally keep keys held between invocations.

## Socket selection

Without `YDOTOOL_SOCKET`, the client tries `/run/ydotoold/socket`. If that service is absent or refuses the connection, it falls back to `$XDG_RUNTIME_DIR/.ydotool_socket`, or `/tmp/.ydotool_socket` when `XDG_RUNTIME_DIR` is unset or empty. Permission errors do not trigger fallback.

Set `YDOTOOL_SOCKET` to select an explicit socket. Explicit overrides disable fallback.

## Build and test

On Debian, build and packaging tools include:

```sh
sudo apt install build-essential cmake git python3 scdoc dpkg-dev xz-utils systemd
```

CMake 3.22 or newer is required. To build the binaries without installing the upstream service templates:

```sh
cmake -S . -B .build/manual -DBUILD_DOCS=OFF \
  -DSYSTEMD_USER_SERVICE=OFF -DSYSTEMD_SYSTEM_SERVICE=OFF
cmake --build .build/manual --parallel
```

To run the isolated regression suite, including UBSan checks, without sending events to the live desktop:

```sh
make test
```

To build a DEB, first commit the intended changes so the checkout is clean, then run:

```sh
make build
```

The package is written to `dist/`. It includes the man pages, license and corresponding source archive. Packaging uses the committed source and records its revision in `X-Source-Commit`.

After installing the package, the optional live sandbox check requires root:

```sh
sudo make test-sandbox
```

This verifies non-root execution, capability and network restrictions, filesystem protection, and access to the uinput device and local socket. It does not type text or move the pointer.

The restricted service described above is installed by the DEB packaging. A direct CMake installation uses the separate upstream service options and does not install this packaging policy.

## License and upstream authors

Licensed under [GNU AGPLv3](LICENSE). The original ydotool was written by ReimuNotMoe; upstream copyright notices and attribution are retained in the source. PosBit maintains the changes in this fork.
