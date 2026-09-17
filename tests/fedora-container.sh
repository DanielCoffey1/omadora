#!/bin/bash
# Disposable-container fixture. This does NOT emulate GDM, a GPU or SELinux.
set -euo pipefail
exec > >(tee /results/fedora-install.log) 2>&1
trap 'status=$?; printf "%s\n" "$status" >/results/exit-status; rpm -qa | sort >/results/packages.txt; exit "$status"' EXIT
cat /etc/os-release
# Supply a Workstation identity so the actual target preflight is exercised.
# This is a container with Workstation identity, not a full Workstation VM.
dnf install -y --allowerasing fedora-release-workstation fedora-release-identity-workstation tuned-ppd sudo git python3 policycoreutils procps-ng
useradd --create-home omadora-test
printf 'omadora-test ALL=(ALL) NOPASSWD: ALL\n' >/etc/sudoers.d/omadora-test
chmod 0440 /etc/sudoers.d/omadora-test
sudo -iu omadora-test python3 /src/tests/fedora-lifecycle.py install
sudo -iu omadora-test bash -c 'cd /src && python3 omadora.py install'
test -s /usr/share/wayland-sessions/omadora.desktop
test -s /etc/pam.d/omarchy-lock-password
test "$(stat -c '%U' /usr/local/share/omadora/omadora.py)" = root
rpm -q tuned-ppd
if rpm -q power-profiles-daemon; then echo 'Conflicting power daemon installed'; exit 1; fi
sudo -iu omadora-test /usr/local/bin/omadora about
sudo -iu omadora-test bash -c 'export PATH=/usr/local/share/omadora/bin:/usr/local/share/omadora/upstream/bin:$PATH; omadora doctor'
sudo -iu omadora-test bash -c 'test -s ~/.local/state/omarchy/current/theme/colors.toml; test -e ~/.local/state/omarchy/current/background'
XDG_RUNTIME_DIR=$(mktemp -d) Hyprland --version
quickshell --version
sudo -iu omadora-test bash /src/tests/fedora-config.sh
XDG_RUNTIME_DIR=$(mktemp -d) Hyprland --help >/results/hyprland-help.txt
sudo -iu omadora-test python3 /src/tests/fedora-apps.py
sudo -iu omadora-test python3 /src/tests/fedora-maintenance.py
sudo -iu omadora-test python3 /src/tests/fedora-lifecycle.py upgrade
cp /tmp/omadora-lifecycle-*.json /results/
cp /tmp/omadora-maintenance.json /results/
cp /tmp/omadora-app-resolution.txt /results/
cp /usr/local/share/omadora/portability-report.json /results/
python3 /src/tests/fedora-legacy.py
echo 'PASS: real Fedora package installation, installer, theme generation and staged files.'
echo 'NOT TESTED: graphical session, GDM, password unlock, suspend, GPU, SELinux.'
