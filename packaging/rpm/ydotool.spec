Name:           ydotool
Version:        @VERSION@
Release:        1%{?dist}
Summary:        PosBit hardened build of ydotool
License:        AGPL-3.0-or-later
URL:            https://github.com/oslyak/ydotool
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  cmake >= 3.22
BuildRequires:  gcc >= 14
BuildRequires:  make
BuildRequires:  scdoc
BuildRequires:  systemd-rpm-macros
%if ! 0%{?suse_version}
BuildRequires:  redhat-rpm-config
%endif
Requires:       systemd
Requires:       kmod
%if 0%{?suse_version}
Requires:       udev
%else
Requires:       systemd-udev
%endif
%{?systemd_requires}

%description
Pinned upstream ydotool with one restricted unprivileged daemon. Authorized
users must be explicitly added to the ydotool group to access its socket.

%prep
%autosetup -n ydotool-%{version}

%build
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=%{_prefix} -DCMAKE_BUILD_TYPE=Release -DBUILD_DOCS=ON \
  -DSYSTEMD_USER_SERVICE=OFF -DSYSTEMD_SYSTEM_SERVICE=OFF \
  -DYDOTOOL_VERSION=posbit-%{version}+upstream.708e96f \
  -DCMAKE_C_FLAGS_RELEASE="-DNDEBUG" \
  -DCMAKE_C_FLAGS="%{optflags}" \
  -DCMAKE_EXE_LINKER_FLAGS="%{?build_ldflags}"
cmake --build build --parallel 2

%install
DESTDIR=%{buildroot} cmake --install build
install -Dpm0644 packaging/ydotoold.service %{buildroot}%{_unitdir}/ydotoold.service
install -Dpm0644 packaging/70-ydotool-uinput.rules %{buildroot}%{_udevrulesdir}/70-ydotool-uinput.rules
install -Dpm0644 packaging/ydotool.sysusers %{buildroot}%{_sysusersdir}/ydotool.conf
install -Dpm0644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE
install -Dpm0644 packaging/SOURCE_REVISION %{buildroot}%{_datadir}/doc/%{name}/SOURCE_REVISION
install -Dpm0644 packaging/ydotool.conf %{buildroot}%{_modulesloaddir}/ydotool.conf

%if 0%{?suse_version}
%pre
%service_add_pre ydotoold.service
%endif

%post
systemd-sysusers %{_sysusersdir}/ydotool.conf || :
if [ -d /run/systemd/system ]; then
  modprobe uinput || :
  udevadm control --reload-rules || :
  if [ -e /sys/class/misc/uinput ]; then
    udevadm trigger --action=change /sys/class/misc/uinput || :
    udevadm settle || :
  fi
fi
%if 0%{?suse_version}
%service_add_post ydotoold.service
%else
%systemd_post ydotoold.service
%endif

%preun
%if 0%{?suse_version}
%service_del_preun ydotoold.service
%else
%systemd_preun ydotoold.service
%endif

%postun
%if 0%{?suse_version}
%service_del_postun ydotoold.service
%else
%systemd_postun_with_restart ydotoold.service
%endif

%files
%{_bindir}/ydotool
%{_bindir}/ydotoold
%{_unitdir}/ydotoold.service
%{_udevrulesdir}/70-ydotool-uinput.rules
%{_sysusersdir}/ydotool.conf
%{_modulesloaddir}/ydotool.conf
%{_licensedir}/%{name}/LICENSE
%{_datadir}/doc/%{name}/SOURCE_REVISION
%{_mandir}/man1/ydotool.1.gz
%{_mandir}/man8/ydotoold.8.gz

%changelog
* Thu Nov 05 2026 PosBit <anton@sirius.if.ua> - 1.0.11-1
- Respect distribution compiler flags and service presets

* Thu Nov 05 2026 PosBit <anton@sirius.if.ua> - 1.0.10-1
- Add native RPM packaging for Fedora and openSUSE
