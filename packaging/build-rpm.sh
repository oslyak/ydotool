#!/usr/bin/env bash
set -euo pipefail
umask 022
cd "$(dirname "$0")/.."
version="$(cat VERSION)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
if [[ ! -e .git ]] || [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
    echo 'ydotool: RPM release requires a clean Git checkout; commit the reviewed source first' >&2
    exit 2
fi
revision="$(git rev-parse HEAD)"
epoch="$(git show -s --format=%ct HEAD)"
export SOURCE_DATE_EPOCH="$epoch"
out="${OUT:-dist}"
mkdir -p "$out"
work="$(mktemp -d "${TMPDIR:-/tmp}/ydotool-rpm.XXXXXX")"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/source/ydotool-$version" "$work/rpmbuild"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
git archive HEAD | tar -xf - -C "$work/source/ydotool-$version"
printf '%s %s\n' "$revision" "$epoch" > "$work/source/ydotool-$version/packaging/SOURCE_REVISION"
tar --sort=name --mode=u+rw,go=r,a+X --mtime="@$epoch" --owner=0 --group=0 --numeric-owner -cf - -C "$work/source" "ydotool-$version" | \
    gzip -n > "$work/rpmbuild/SOURCES/ydotool-$version.tar.gz"
sed "s/@VERSION@/$version/g" packaging/rpm/ydotool.spec > "$work/rpmbuild/SPECS/ydotool.spec"
rpmbuild -ba --define "_topdir $work/rpmbuild" "$work/rpmbuild/SPECS/ydotool.spec"
find "$work/rpmbuild/RPMS" -type f -name "ydotool-$version-*.rpm" -exec cp -t "$out" {} +
mkdir -p "$out/source"
find "$work/rpmbuild/SRPMS" -type f -name "ydotool-$version-*.src.rpm" -exec cp -t "$out/source" {} +
find "$out" -maxdepth 1 -type f -name '*.rpm' -print
