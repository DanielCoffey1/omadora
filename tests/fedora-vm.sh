#!/bin/bash
# Disposable CI VM: Cloud + Workstation packages, or an Anaconda-installed disk.
# Test credentials and autologin exist only inside this ephemeral VM.
set -euo pipefail
mkdir -p vm-results /tmp/omadora-vm
exec > >(tee vm-results/host.log) 2>&1
task_root=$PWD
vm_dir=/tmp/omadora-vm
if [[ ${VM_BASE:-cloud} == workstation-iso ]]; then
  if [[ ${VM_ISO_PREPARED:-0} != 1 ]]; then bash tests/fedora-workstation-iso.sh; fi
else
image=Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2
base=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images
curl -fL --retry 3 "$base/$image" -o "$vm_dir/disk.qcow2"
curl -fL --retry 3 "$base/Fedora-Cloud-44-1.7-x86_64-CHECKSUM" -o "$vm_dir/CHECKSUM"
expected=$(sed -n "s/^SHA256 ($image) = //p" "$vm_dir/CHECKSUM")
[[ $expected =~ ^[0-9a-f]{64}$ ]]
printf '%s  %s\n' "$expected" "$vm_dir/disk.qcow2" | sha256sum -c -
qemu-img resize "$vm_dir/disk.qcow2" 60G
ssh-keygen -q -t ed25519 -N '' -f "$vm_dir/key"
pubkey=$(cat "$vm_dir/key.pub")
cat >"$vm_dir/user-data" <<EOF
#cloud-config
preserve_hostname: true
users:
  - name: omadora-test
    groups: wheel
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: false
    plain_text_passwd: omadora-vm-test-only
    ssh_authorized_keys:
      - $pubkey
EOF
printf 'instance-id: omadora-ci\nlocal-hostname: omadora-ci\n' >"$vm_dir/meta-data"
cloud-localds "$vm_dir/seed.img" "$vm_dir/user-data" "$vm_dir/meta-data"
fi
boot_drives=(-drive "file=$vm_dir/seed.img,format=raw,if=virtio")
if [[ ${VM_BASE:-cloud} == workstation-iso ]]; then
  boot_drives=(-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
               -drive "if=pflash,format=raw,file=$vm_dir/OVMF_VARS.fd")
fi
accel=tcg
cpu=max
if [[ -e /dev/kvm ]]; then sudo chmod 0666 /dev/kvm; accel=kvm; cpu=host; fi
echo "VM acceleration: $accel"
Xvfb :99 -screen 0 1920x1080x24 >vm-results/xvfb.log 2>&1 &
xvfb_pid=$!
export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1
# GTK must connect after Xvfb is accepting clients, otherwise QEMU can fall
# back to a display backend without OpenGL before the guest even boots.
for ((attempt=0; attempt<100; attempt++)); do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then break; fi
  kill -0 "$xvfb_pid"
  sleep 0.1
done
xdpyinfo -display "$DISPLAY" >/dev/null
graphics=(-device virtio-vga-gl -display gtk,gl=on)
if [[ ${VM_SLEEP_DIAGNOSTIC:-} == software-gpu ]]; then
  graphics=(-device virtio-vga -display gtk,gl=off)
elif [[ ${VM_SLEEP_DIAGNOSTIC:-} == bochs-gpu ]]; then
  # bochs-display is not a VGA device, so suppress QEMU's automatic std VGA.
  graphics=(-vga none -device bochs-display -display gtk,gl=off)
fi
qemu-system-x86_64 -accel "$accel" -cpu "$cpu" -m 4096 -smp 2 \
  -drive "file=$vm_dir/disk.qcow2,if=virtio,format=qcow2" \
  "${boot_drives[@]}" \
  "${graphics[@]}" \
  -audiodev driver=none,id=audio0 -device intel-hda -device hda-duplex,audiodev=audio0 \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=net0 \
  -serial "file:$task_root/vm-results/serial.log" \
  -qmp "unix:$vm_dir/qmp.sock,server=on,wait=off" >vm-results/qemu.log 2>&1 &
qemu_pid=$!
cleanup() {
  status=$?
  scp -r -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 omadora-test@127.0.0.1:/tmp/omadora-vm-results/. vm-results/ 2>/dev/null || true
  scp -r -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 omadora-test@127.0.0.1:.cache/hyprland vm-results/hyprland-crashes 2>/dev/null || true
  ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'sudo journalctl -b --no-pager' >vm-results/guest-journal.log 2>&1 || true
  ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'cat /run/user/1000/hypr/*/hyprland.log' >vm-results/hyprland-runtime.log 2>&1 || true
  kill "$qemu_pid" "$xvfb_pid" 2>/dev/null || true
  exit "$status"
}
ssh_options=(-i "$vm_dir/key" -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o BatchMode=yes)
trap cleanup EXIT
wait_ssh() {
  for ((attempt=0; attempt<90; attempt++)); do
    kill -0 "$qemu_pid" || { cat vm-results/qemu.log; return 1; }
    if ssh "${ssh_options[@]}" omadora-test@127.0.0.1 true 2>/dev/null; then return 0; fi
    sleep 3
  done
  return 1
}
wait_ssh
if [[ ${VM_BASE:-cloud} != workstation-iso ]]; then
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'sudo cloud-init status --wait --format json >/tmp/cloud-status.json; cat /tmp/cloud-status.json; python3 -c '\''import json; s=json.load(open("/tmp/cloud-status.json")); assert s["status"] == "done" and not s.get("errors"), s'\'''
else
  ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'set -e; cat /etc/os-release; cat /proc/cmdline; ! grep -Eq "systemd.debug_shell|systemd.mask=systemd-firstboot|inst.webui.remote" /proc/cmdline; test -d /sys/firmware/efi; test "$(getenforce)" = Enforcing; rpm -q fedora-release-workstation; findmnt /; lsblk -f' | tee vm-results/workstation-baseline.log
fi
if [[ -n ${OMADORA_TEST_APPS:-} ]]; then
  python3 - <<'PY'
import json, os
from pathlib import Path
selection = [item.strip() for item in os.environ['OMADORA_TEST_APPS'].split(',') if item.strip()]
assert selection and len(selection) == len(set(selection)) and set(selection) <= set(json.loads(Path('apps.json').read_text()))
Path('tests/selected-apps.json').write_text(json.dumps(selection))
PY
fi
tar --exclude=.git --exclude=__pycache__ -czf "$vm_dir/source.tar.gz" omadora.py omadora_deploy.py omadora_lifecycle.py omadora_optional.py omadora_workflows.py apps.json optional.json upstream.lock.json packages assets tests
scp -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$vm_dir/source.tar.gz" omadora-test@127.0.0.1:/tmp/source.tar.gz
revision=$(git rev-parse HEAD)
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 "bash -s -- ${VM_SLEEP_DIAGNOSTIC:-default} $revision ${VM_BASE:-cloud}" <<'GUEST'
set -euo pipefail
if [[ $3 != workstation-iso ]]; then
sudo dnf --setopt=max_parallel_downloads=10 install -y --allowerasing @workstation-product-environment fedora-release-identity-workstation
# Cloud starts with a trimmed kernel; install Workstation's kernel metapackage
# so the emulated sound device has its normal driver after reboot.
sudo dnf install -y kernel python3-pexpect
else
  # Test instrumentation only; the desktop and kernel came from the Live ISO.
  sudo dnf install -y python3-pexpect
fi
mkdir -p ~/source
tar -xzf /tmp/source.tar.gz -C ~/source
cd ~/source
mkdir -p ~/.config/hypr
printf 'pre-install sentinel\n' >~/.config/hypr/original-test-marker
# Exercise the public bootstrap at the workflow revision. A newer push must not
# silently replace the code under test while this VM is still downloading.
curl -fsSL "https://raw.githubusercontent.com/DanielCoffey1/omadora/$2/boot.sh" | OMADORA_REF="$2" bash
cmp omadora.py /usr/local/share/omadora/omadora.py
if [[ $1 == startup-race ]]; then
  # Reproduce a slow GDM launch that lets the greeter retain the active VT.
  printf '#!/bin/bash\nsleep 12\nexec /usr/local/bin/omadora-session\n' | sudo tee /usr/local/bin/omadora-test-delayed-session >/dev/null
  sudo chmod 755 /usr/local/bin/omadora-test-delayed-session
  sudo sed -i 's|Exec=/usr/local/bin/omadora-session|Exec=/usr/local/bin/omadora-test-delayed-session|' /usr/share/wayland-sessions/omadora.desktop
fi
if [[ $1 == legacy-drm ]]; then
  # Diagnostic only. Upstream discourages legacy DRM for normal use:
  # https://github.com/hyprwm/aquamarine/blob/main/docs/env.md
  printf '\nexport AQ_NO_ATOMIC=1\n' >>~/.config/uwsm/env-hyprland
fi
printf 'post-install sentinel\n' >~/.config/hypr/post-install-marker
# The virtual monitor advertises 640x480 as preferred. Use a normal desktop
# mode for visual evidence through the default rule. A second connector rule
# pinned to scale=1 overrides every scaling change when this file reloads.
# This file is confined to the disposable test user.
sed -i \
  -e 's/^local omarchy_monitor_scale = .*/local omarchy_monitor_scale = 1/' \
  -e 's/^local omarchy_gdk_scale = .*/local omarchy_gdk_scale = 1/' \
  -e 's/mode = "preferred"/mode = "1920x1080@60"/' ~/.config/hypr/monitors.lua
sudo mkdir -p /var/lib/AccountsService/users
printf '[User]\nXSession=omadora\nSession=omadora\nSystemAccount=false\n' | sudo tee /var/lib/AccountsService/users/omadora-test >/dev/null
printf '[daemon]\nAutomaticLoginEnable=True\nAutomaticLogin=omadora-test\n' | sudo tee /etc/gdm/custom.conf >/dev/null
sudo systemctl enable gdm
sudo systemctl set-default graphical.target
GUEST
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'sudo systemctl reboot' || true
sleep 15
wait_ssh
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'bash ~/source/tests/fedora-vm-guest.sh'
if [[ ${VM_SUITE:-apps} == system ]]; then
  python3 tests/fedora-vm-system.py
elif [[ ${VM_SUITE:-apps} == keybindings ]]; then
  python3 tests/fedora-vm-keybindings.py
elif [[ ${VM_SUITE:-apps} == diagnostic ]]; then
  if [[ ${VM_SLEEP_DIAGNOSTIC:-} =~ ^(reliability|startup-race|software-gpu|bochs-gpu|quiesce-gpu)$ ]]; then
    python3 tests/fedora-vm-reliability.py
  else
    python3 tests/fedora-vm-interactions.py
  fi
else
  # Suspend is deliberately last: a driver/compositor hang must not prevent
  # collection of independent application results from a healthy desktop.
  ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'bash -c '\''source ~/source/tests/vm-session.sh; python3 ~/source/tests/fedora-vm-apps.py'\'''
  python3 tests/fedora-vm-interactions.py
fi
scp -r -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null omadora-test@127.0.0.1:/tmp/omadora-vm-results/. vm-results/
python3 - <<'PY'
import json
from pathlib import Path
interactions = json.loads(Path('vm-results/interactions.json').read_text())
assert all(r['status'] == 'PASS' for r in interactions), interactions
if Path('vm-results/apps/results.json').exists():
    apps = json.loads(Path('vm-results/apps/results.json').read_text())
    selection_file = Path('vm-results/apps/selection.json')
    expected = json.loads(selection_file.read_text()) if selection_file.exists() else list(json.loads(Path('apps.json').read_text()))
    assert {r['app'] for r in apps} == set(expected) and all('error' not in r and not r['remove'].startswith('FAIL') for r in apps), apps
PY
echo 'PASS: booted Fedora VM, GDM autologin, Hyprland, Quickshell IPC and screenshots.'
