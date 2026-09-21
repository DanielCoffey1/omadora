#!/bin/bash
# Boot actual ISO UEFI media and install on a blank virtual disk, without WAN.
set -euo pipefail
vm_dir=/tmp/omadora-vm
mkdir -p "$vm_dir" vm-results
iso=$(realpath iso-results/test/omadora-test.iso)
qemu-img create -f qcow2 "$vm_dir/disk.qcow2" 60G
ssh-keygen -q -t ed25519 -N '' -f "$vm_dir/key"
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$vm_dir/OVMF_VARS.fd"
accel=tcg; cpu=max
if [[ -e /dev/kvm ]]; then sudo chmod 0666 /dev/kvm; accel=kvm; cpu=host; fi
Xvfb :98 -screen 0 1920x1080x24 >vm-results/iso-xvfb.log 2>&1 &
xvfb_pid=$!
export DISPLAY=:98 LIBGL_ALWAYS_SOFTWARE=1
for ((i=0; i<100; i++)); do xdpyinfo >/dev/null 2>&1 && break; sleep .1; done
common=(-accel "$accel" -cpu "$cpu" -m 4096 -smp 2
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
  -drive "if=pflash,format=raw,file=$vm_dir/OVMF_VARS.fd"
  -drive "file=$vm_dir/disk.qcow2,if=virtio,format=qcow2"
  -device qemu-xhci,id=omadora-usb -device usb-tablet,bus=omadora-usb.0
  -netdev user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:2222-:22
  -device virtio-net-pci,netdev=net0)
# The installer compositor uses guest software rendering. Keeping it off the
# host virgl path also allows QMP diagnostics if its graphics startup stalls.
qemu-system-x86_64 "${common[@]}" -device virtio-vga -display gtk \
  -drive "if=none,file=$iso,format=raw,readonly=on,id=installer" \
  -device usb-storage,bus=omadora-usb.0,drive=installer,bootindex=1 \
  -serial "unix:$vm_dir/iso-serial.sock,server=on,wait=off" \
  -qmp "unix:$vm_dir/iso-qmp.sock,server=on,wait=off" >vm-results/iso-qemu.log 2>&1 &
qemu_pid=$!
ssh_options=(-i "$vm_dir/key" -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o BatchMode=yes)
cleanup() {
  status=$?
  ssh "${ssh_options[@]}" root@127.0.0.1 'systemctl list-jobs --no-pager; systemctl status anaconda-pre anaconda anaconda-direct --no-pager; ps -eo pid,ppid,stat,wchan,args; cat /usr/lib/systemd/system/anaconda-pre.service; journalctl -b --no-pager; cat /tmp/anaconda.log /tmp/packaging.log /tmp/program.log 2>/dev/null' >vm-results/iso-guest.log 2>&1 || true
  ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'sudo journalctl -b --no-pager' >vm-results/installed-journal.log 2>&1 || true
  python3 - <<'PY' || true
import json, socket
from pathlib import Path
path = Path('/tmp/omadora-vm/qmp.sock')
if not path.exists(): path = Path('/tmp/omadora-vm/iso-qmp.sock')
s = socket.socket(socket.AF_UNIX); s.settimeout(5); s.connect(str(path))
f = s.makefile('rwb'); f.readline()
for command in ({'execute': 'qmp_capabilities'}, {'execute': 'screendump', 'arguments': {'filename': str(Path('vm-results/iso-console.png').resolve()), 'format': 'png'}}):
    f.write((json.dumps(command)+'\n').encode()); f.flush()
    while True:
        response = json.loads(f.readline())
        if 'return' in response or 'error' in response: break
PY
  scp -r -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 \
    omadora-test@127.0.0.1:/tmp/omadora-vm-results/. vm-results/ 2>/dev/null || true
  kill "$qemu_pid" "$xvfb_pid" 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT
OMADORA_CUSTOM_ISO=1 python3 tests/fedora-workstation-install.py
# Test access and display dimensions only. Account/configuration comes from ISO.
scp -r -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null tests root@127.0.0.1:/mnt/sysroot/home/omadora-test/source-tests
ssh "${ssh_options[@]}" root@127.0.0.1 'bash -s' <<'GUEST'
set -eu
target=/mnt/sysroot
test -f "$target/etc/omadora/image.json"
grep -q 'Session=omadora' "$target/var/lib/AccountsService/users/omadora-test"
mkdir -p "$target/home/omadora-test/source"
mv "$target/home/omadora-test/source-tests" "$target/home/omadora-test/source/tests"
chroot "$target" chown -R omadora-test:omadora-test /home/omadora-test/source
printf '[daemon]\nDefaultSession=omadora.desktop\nAutomaticLoginEnable=True\nAutomaticLogin=omadora-test\n' >"$target/etc/gdm/custom.conf"
sed -i -e 's/^local omarchy_monitor_scale = .*/local omarchy_monitor_scale = 1/' \
  -e 's/^local omarchy_gdk_scale = .*/local omarchy_gdk_scale = 1/' \
  -e 's/mode = "preferred"/mode = "1920x1080@60"/' \
  "$target/usr/local/share/omadora/upstream/config/hypr/monitors.lua"
sync
systemctl poweroff
GUEST
for ((i=0; i<90; i++)); do kill -0 "$qemu_pid" 2>/dev/null || break; sleep 1; done
kill -0 "$qemu_pid" 2>/dev/null && exit 1
# No CD or injected kernel/initrd: boot only the installed disk through UEFI.
qemu-system-x86_64 "${common[@]}" -device virtio-vga-gl -display gtk,gl=on -boot order=c \
  -serial "file:$(pwd)/vm-results/installed-serial.log" \
  -qmp "unix:$vm_dir/qmp.sock,server=on,wait=off" >vm-results/installed-qemu.log 2>&1 &
qemu_pid=$!
for ((i=0; i<90; i++)); do
  if ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'test -f ~/.local/state/omadora/image-user.json'; then break; fi
  sleep 3
done
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'set -eu; test -f ~/.local/state/omadora/image-user.json; test -d /sys/firmware/efi; getenforce | grep Enforcing; if curl -fsS --connect-timeout 3 --max-time 5 https://example.com; then exit 1; fi; mkdir -p /tmp/omadora-vm-results; cp ~/.local/state/omadora/image-user.json ~/.local/state/omadora/installation.json /tmp/omadora-vm-results/'
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'if grep -Eq "systemd.debug_shell|inst.sshd" /proc/cmdline; then echo "Installer debug access leaked into installed boot configuration" >&2; exit 1; fi'
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'bash ~/source/tests/fedora-vm-guest.sh'
python3 tests/fedora-vm-wallpapers.py
echo 'PASS: offline UEFI ISO installation, installer-created account, Omadora first login, wallpaper apply/import/remove.'
