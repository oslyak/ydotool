#!/usr/bin/env bash
set -euo pipefail
umask 022
export LC_ALL=C
cd "$(dirname "$0")/.."
mode="${1:?test or package}"
[[ "$mode" == test || "$mode" == package ]]
upstream=708e96ff27e381a8c549418a9d34cdde12305317
version="$(cat VERSION)"
package_version="${version}+upstream.${upstream:0:7}"
if [[ "$mode" == package ]]; then
    if [[ ! -e .git ]] || [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
        echo 'ydotool: release requires a clean Git checkout; commit the reviewed source first' >&2
        exit 2
    fi
    python3 po/check_catalogs.py --strict --require-reviewed dz
fi
if [[ -e .git ]]; then
    source_revision="$(git rev-parse HEAD)"
    SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
else
    read -r source_revision SOURCE_DATE_EPOCH < SOURCE_REVISION
fi
export SOURCE_DATE_EPOCH
mkdir -p .build
work="$(mktemp -d "$PWD/.build/${mode}.XXXXXX")"
trap 'rm -rf "$work"' EXIT
mkdir "$work/source"
if [[ "$mode" == package ]]; then
    git archive HEAD | tar -xf - -C "$work/source"
else
    tar --exclude=./.git --exclude=./.build --exclude=./dist -cf - . | \
        tar -xf - -C "$work/source"
fi
printf '%s %s\n' "$source_revision" "$SOURCE_DATE_EPOCH" > "$work/source/SOURCE_REVISION"
flags='-O2 -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fPIE'
link_flags='-Wl,-z,relro,-z,now -pie'
if [[ "$mode" == test ]]; then
    flags+=' -fsanitize=undefined -fno-sanitize-recover=all'
    link_flags+=' -fsanitize=undefined'
fi
cmake -S "$work/source" -B "$work/build" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DBUILD_DOCS=OFF -DCMAKE_INSTALL_PREFIX=/usr -DYDOTOOL_TESTS=ON -DSYSTEMD_USER_SERVICE=OFF -DSYSTEMD_SYSTEM_SERVICE=OFF \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    "-DYDOTOOL_VERSION=posbit-${package_version}" "-DCMAKE_C_FLAGS=$flags" \
    "-DCMAKE_EXE_LINKER_FLAGS=$link_flags"
cmake --build "$work/build" --parallel 2
python3 - "$work/build/compile_commands.json" <<'PY'
import json
import sys

commands = json.load(open(sys.argv[1], encoding="utf-8"))
assert commands and all(any(flag in entry["command"] for flag in ("-std=gnu2x", "-std=gnu23")) for entry in commands)
PY
[[ "$("$work/build/ydotoold" --version)" == "posbit-${package_version}" ]]
python3 "$work/source/tests/socket_paths_test.py" "$work/build/socket_paths"
python3 "$work/source/tests/input_test.py" "$work/build/ydotool"
python3 "$work/source/tests/source_test.py"
python3 "$work/source/tests/catalog_test.py"
python3 "$work/source/tests/release_gate_test.py"
python3 "$work/source/tests/gettext_test.py" "$work/build/ydotool"
python3 "$work/source/po/check_catalogs.py"
python3 "$work/source/tests/package_test.py"
python3 "$work/source/tests/rpm_test.py"
python3 "$work/source/tests/cmake_test.py"
python3 "$work/source/tests/daemon_test.py" "$work/build/ydotoold" "$work/build/libfake_uinput.so"
set +e
"$work/build/send_failure"
status=$?
set -e
[[ "$status" == 2 ]]
if [[ "$mode" == test ]]; then
    mkdir "$work/verify"
    sed "s|/usr/bin/ydotoold|$work/build/ydotoold|g" \
        "$work/source/packaging/ydotoold.service" > "$work/verify/ydotoold.service"
    systemd-analyze verify "$work/verify/"*
    exit 0
fi
root="$work/package"
install -D -m 755 "$work/build/ydotool" "$root/usr/bin/ydotool"
install -D -m 755 "$work/build/ydotoold" "$root/usr/bin/ydotoold"
mkdir -p "$root/usr/share/locale"
cp -a "$work/build/locale/." "$root/usr/share/locale/"
install -D -m 644 "$work/source/packaging/ydotoold.service" "$root/usr/lib/systemd/system/ydotoold.service"
install -D -m 644 "$work/source/packaging/70-ydotool-uinput.rules" "$root/usr/lib/udev/rules.d/70-ydotool-uinput.rules"
install -D -m 644 "$work/source/packaging/ydotool.sysusers" "$root/usr/lib/sysusers.d/ydotool.conf"
install -D -m 644 "$work/source/LICENSE" "$root/usr/share/doc/ydotool/copyright"
mkdir -p "$root/usr/lib/modules-load.d" "$root/DEBIAN" "$root/usr/share/man/man1" "$root/usr/share/man/man8"
scdoc < "$work/source/manpage/ydotool.1.scd" | gzip -n -9 > "$root/usr/share/man/man1/ydotool.1.gz"
scdoc < "$work/source/manpage/ydotoold.8.scd" | gzip -n -9 > "$root/usr/share/man/man8/ydotoold.8.gz"
printf 'uinput\n' > "$root/usr/lib/modules-load.d/ydotool.conf"
for hook in postinst prerm postrm; do
    install -m 755 "$work/source/packaging/$hook" "$root/DEBIAN/$hook"
done
tar --sort=name --mode=u+rw,go=r,a+X --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
    -cJf "$root/usr/share/doc/ydotool/source.tar.xz" -C "$work" source
strip --strip-unneeded "$root/usr/bin/ydotool" "$root/usr/bin/ydotoold"
install -m 644 "$work/source/SOURCE_REVISION" "$root/usr/share/doc/ydotool/source-revision"
changelog_date="$(date -u -d "@$SOURCE_DATE_EPOCH" -R)"
{
    printf 'ydotool (%s) unstable; urgency=medium\n\n' "$package_version"
    printf '  * Localize client and daemon through GNU gettext.\n'
    printf '  * Preserve hardened input handling and source provenance.\n\n'
    printf ' -- PosBit <anton@sirius.if.ua>  %s\n' "$changelog_date"
} | gzip -n -9 > "$root/usr/share/doc/ydotool/changelog.gz"
mkdir -p "$work/debian"
printf 'Source: ydotool\n' > "$work/debian/control"
libc_dep="$(cd "$work" && dpkg-shlibdeps -O "$root/usr/bin/ydotool" "$root/usr/bin/ydotoold" | sed -n 's/^shlibs:Depends=//p')"
[[ -n "$libc_dep" ]]
cat > "$root/DEBIAN/control" <<CONTROL
Package: ydotool
Version: ${package_version}
Architecture: $(dpkg --print-architecture)
Maintainer: PosBit <anton@sirius.if.ua>
Section: utils
Priority: optional
Depends: ${libc_dep}, systemd, udev, kmod, init-system-helpers (>= 1.54~)
Homepage: https://github.com/ReimuNotMoe/ydotool
Description: PosBit hardened build of ydotool
 Pinned upstream ${upstream}. Includes ASCII input
 validation, an explicit version, and one unprivileged service
 with network and device restrictions.
 Add authorized users to the ydotool group to access /run/ydotoold/socket.
 YDOTOOL_SOCKET can select another socket.
 Non-ASCII text requires clipboard paste.
CONTROL
out="${OUT:-dist}"
mkdir -p "$out"
find "$root" -type d -exec chmod 755 {} +
find "$root" -type f ! -perm /111 -exec chmod 644 {} +
package="$out/ydotool_${package_version}_$(dpkg --print-architecture).deb"
dpkg-deb --root-owner-group -Zxz --build "$root" "$package"
lintian --fail-on error,warning "$package"
