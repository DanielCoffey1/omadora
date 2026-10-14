#!/bin/bash
# Disposable-container fixture. This does NOT emulate GDM, a GPU or SELinux.
set -euo pipefail
exec > >(tee /results/fedora-install.log) 2>&1
trap 'status=$?; printf "%s\n" "$status" >/results/exit-status; rpm -qa | sort >/results/packages.txt; exit "$status"' EXIT
cat /etc/os-release
# Exercise both supported edition identities, without claiming desktop coverage.
edition=${OMADORA_TEST_EDITION:-workstation}
case "$edition" in
  workstation|kde) ;;
  *) echo 'Unsupported fixture edition' >&2; exit 1 ;;
esac
dnf install -y --allowerasing "fedora-release-$edition" "fedora-release-identity-$edition" tuned-ppd sudo git python3 policycoreutils procps-ng
if [[ $edition == kde ]]; then
  # Reproduce the old package shipped on the owner's Fedora KDE media.
  # The installer itself must perform its rename migration, not this fixture.
  dnf install -y --setopt=install_weak_deps=False https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/k/kmime-25.12.3-1.fc44.x86_64.rpm
  rpm -q kmime
fi
useradd --create-home omadora-test
printf 'omadora-test ALL=(ALL) NOPASSWD: ALL\n' >/etc/sudoers.d/omadora-test
chmod 0440 /etc/sudoers.d/omadora-test
sudo -iu omadora-test python3 /src/tests/fedora-lifecycle.py install
sudo -iu omadora-test bash -c 'cd /src && python3 omadora.py install'
test -s /usr/share/wayland-sessions/omadora.desktop
test -s /etc/pam.d/omarchy-lock-password
if [[ $edition == kde ]]; then
  ! rpm -q kmime
  rpm -q kf6-kmime sddm sddm-x11
  grep -Fx 'DisplayServer=x11' /etc/sddm.conf.d/90-omadora.conf
  grep -Fx 'InputMethod=' /etc/sddm.conf.d/90-omadora.conf
  grep -Fx 'GreeterEnvironment=QT_QUICK_BACKEND=software' /etc/sddm.conf.d/90-omadora.conf
fi
test "$(stat -c '%U' /usr/local/share/omadora/omadora.py)" = root
python3 /src/tests/fedora-image.py
rpm -q tuned-ppd
if rpm -q power-profiles-daemon; then echo 'Conflicting power daemon installed'; exit 1; fi
sudo -iu omadora-test /usr/local/bin/omadora about
sudo -iu omadora-test bash -c 'export PATH=/usr/local/share/omadora/bin:/usr/local/share/omadora/upstream/bin:$PATH; omadora doctor'
sudo -iu omadora-test bash -c 'test -s ~/.local/state/omarchy/current/theme/colors.toml; test -e ~/.local/state/omarchy/current/background'
XDG_RUNTIME_DIR=$(mktemp -d) Hyprland --version
quickshell --version
sudo -iu omadora-test python3 /src/tests/fedora-wallpapers.py
sudo -iu omadora-test bash /src/tests/fedora-config.sh
sudo -iu omadora-test python3 /src/tests/fedora-app-refresh.py
cp /tmp/omadora-app-refresh.log /results/
XDG_RUNTIME_DIR=$(mktemp -d) Hyprland --help >/results/hyprland-help.txt
sudo -iu omadora-test python3 /src/tests/fedora-apps.py
sudo -iu omadora-test python3 /src/tests/fedora-maintenance.py
sudo -iu omadora-test python3 /src/tests/fedora-lifecycle.py upgrade
cp /tmp/omadora-lifecycle-*.json /results/
cp /tmp/omadora-maintenance.json /results/
cp /tmp/omadora-app-resolution.txt /results/
cp /usr/local/share/omadora/portability-report.json /results/
if [[ $edition == workstation ]]; then
  python3 /src/tests/fedora-legacy.py
else
  # The actual historical release intentionally rejects KDE. Test its upgrade
  # path on Workstation; do not misreport that rejection as a current failure.
  printf '%s\n' 'NOT APPLICABLE: historical Workstation-only release on KDE' >/results/legacy-edition.txt
fi
echo 'PASS: real Fedora package installation, installer, theme generation and staged files.'
echo 'NOT TESTED: graphical session, GDM, password unlock, suspend, GPU, SELinux.'
