# ydotool 1.0.10 — Test Report

**Date:** 5 November 2026  
**Release:** [GitHub packages and source RPMs](https://github.com/oslyak/ydotool/releases/tag/posbit-1.0.10)  
**Build source:** [1c5cc2f](https://github.com/oslyak/ydotool/commit/1c5cc2fd298f3137dcbd19c0b3cc92a660da547c)  
**CI:** [All five validation jobs passed](https://github.com/oslyak/ydotool/actions/runs/41892053279)

## Platform coverage

| Platform | Build, 32 tests, package installation | Runtime verification | GUI verification |
|---|---|---|---|
| Debian 13.7 amd64 | Passed | QEMU/KVM guest | X11 and Wayland |
| Ubuntu 24.04.5 amd64 | Passed | QEMU/KVM guest | Not tested |
| Fedora 43 x86_64 | Passed | QEMU/KVM guest | Not tested |
| openSUSE Leap 16.0 x86_64 | Passed | QEMU/KVM guest, full kernel required | Not tested |
| Debian 13.7 ARM64 | Passed on a native ARM64 CI runner | QEMU/TCG guest | Not tested |

ARM64 runtime testing executed the ARM64 binaries and kernel under CPU emulation. Physical ARM hardware was not tested.

## Build and regression testing

- C23 compilation with GNU extensions was confirmed.
- The CI matrix completed 32 regression tests per target with UndefinedBehaviorSanitizer enabled.
- GCC 14 and GCC 15 were exercised across distributions. Earlier C23 validation also passed with Clang 19.
- Native DEB and RPM packages were built and installed successfully.

## Runtime and package lifecycle

The VM checks verified:

- Automatic daemon startup after installation and reboot.
- Execution as the dedicated `ydotool` user, without root privileges or capabilities.
- Socket ownership `ydotool:ydotool` and permissions `0660`.
- Successful access for authorized group members and rejection of unauthorized users.
- Keyboard events, Ctrl+A, pointer movement, clicks and `release-all` through actual kernel evdev devices.
- Network restrictions, protected system files and home directories, and permitted access to `/dev/uinput`.
- Reinstallation, removal and subsequent installation.
- Preservation of administrator service disablement.

The Debian amd64 upgrade from version 1.0.9 to 1.0.10 was also verified.

## Graphical input

**X11:** Debian VM testing confirmed keyboard and pointer delivery using `xev`.

**Wayland:** Debian amd64 ran Weston 14.0.2 through native DRM/KMS with a virtual GPU and the Pixman renderer. Both compositor and client ran as an ordinary user.

The native Wayland `wev` client received:

- Text `c23`.
- Ctrl+A.
- Pointer movement and left-button press/release.
- `release-all`, followed by normal `b` input confirming modifier release.

## Issues identified and resolved

- Incorrect RPM license metadata was corrected to `AGPL-3.0-or-later`.
- RPM installation now loads `uinput` and settles udev before starting the daemon.
- CI container environment handling and artifact collection were corrected.
- Fedora debug-source generation was fixed by retaining debugging information.

The minimal openSUSE cloud image lacked `uinput` in its initial kernel. Runtime checks passed after booting the full `kernel-default` package, version `6.12.0-160000.39-default`.

## Artifact integrity and limits

GitHub downloads were checked against the tested artifacts using SHA-256. The Debian amd64 package matched the local and CI builds byte for byte. The APT repository signature and package checksum were verified.

KDE/KWin, GNOME/Mutter, Sway, ARM64 graphics and physical ARM hardware remain outside this test coverage. All task-owned test VMs were stopped after verification.
