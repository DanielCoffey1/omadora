#!/bin/bash
# Install an unmodified official Live ISO onto a new disposable virtual disk.
# Automation access exists only in this guest; no host disk is attached.
set -euo pipefail
vm_dir=/tmp/omadora-vm
mkdir -p "$vm_dir" vm-results
image=Fedora-Workstation-Live-44-1.7.x86_64.iso
base=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Workstation/x86_64/iso
curl -fL --retry 3 "$base/$image" -o "$vm_dir/workstation.iso"
curl -fL --retry 3 "$base/Fedora-Workstation-44-1.7-x86_64-CHECKSUM" -o "$vm_dir/workstation-CHECKSUM"
expected=$(sed -n "s/^SHA256 ($image) = //p" "$vm_dir/workstation-CHECKSUM")
[[ $expected =~ ^[0-9a-f]{64}$ ]]
printf '%s  %s\n' "$expected" "$vm_dir/workstation.iso" | sha256sum -c -
cp "$vm_dir/workstation-CHECKSUM" vm-results/
xorriso -indev "$vm_dir/workstation.iso" -find / -type f -exec echo >"$vm_dir/iso-files.txt"
cp "$vm_dir/iso-files.txt" vm-results/iso-files.txt
xorriso -osirrox on -indev "$vm_dir/workstation.iso" -extract /boot/grub2/grub.cfg "$vm_dir/iso-grub.cfg"
cp "$vm_dir/iso-grub.cfg" vm-results/iso-grub.cfg
cat "$vm_dir/iso-grub.cfg"
mapfile -t boot_files < <(python3 - "$vm_dir/iso-files.txt" <<'PY'
import shlex, sys
from pathlib import PurePosixPath
paths = shlex.split(open(sys.argv[1]).read())
for names in ({'vmlinuz', 'linux'}, {'initrd.img', 'initrd'}):
    matches = [p for p in paths if PurePosixPath(p).name in names]
    assert len(matches) == 1, matches
    print(matches[0])
PY
)
[[ ${#boot_files[@]} == 2 ]]
xorriso -osirrox on -indev "$vm_dir/workstation.iso" -extract "${boot_files[0]}" "$vm_dir/vmlinuz"
xorriso -osirrox on -indev "$vm_dir/workstation.iso" -extract "${boot_files[1]}" "$vm_dir/initrd.img"
label=$(xorriso -indev "$vm_dir/workstation.iso" -pvd_info 2>/dev/null | sed -n 's/^Volume [Ii]d *: //p' | tr -d "'")
[[ -n $label ]]
qemu-img create -f qcow2 "$vm_dir/disk.qcow2" 60G
ssh-keygen -q -t ed25519 -N '' -f "$vm_dir/key"
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$vm_dir/OVMF_VARS.fd"
accel=tcg; cpu=max
if [[ -e /dev/kvm ]]; then sudo chmod 0666 /dev/kvm; accel=kvm; cpu=host; fi
echo "Live ISO acceleration: $accel"
Xvfb :98 -screen 0 1920x1080x24 >vm-results/iso-xvfb.log 2>&1 &
xvfb_pid=$!
export DISPLAY=:98 LIBGL_ALWAYS_SOFTWARE=1
for ((i=0; i<100; i++)); do xdpyinfo >/dev/null 2>&1 && break; sleep .1; done
qemu-system-x86_64 -accel "$accel" -cpu "$cpu" -m 4096 -smp 2 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive "if=pflash,format=raw,file=$vm_dir/OVMF_VARS.fd" \
  -drive "file=$vm_dir/disk.qcow2,if=virtio,format=qcow2" \
  -drive "file=$vm_dir/workstation.iso,media=cdrom,readonly=on" \
  -kernel "$vm_dir/vmlinuz" -initrd "$vm_dir/initrd.img" \
  -append "root=live:CDLABEL=$label rd.live.image edd=off console=tty0 console=ttyS0,115200 systemd.debug_shell=ttyS0 inst.graphical inst.webui inst.webui.remote inst.webui.remote.noauth" \
  -device virtio-vga-gl -display gtk,gl=on \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22,hostfwd=tcp:127.0.0.1:9443-:443,hostfwd=tcp:127.0.0.1:9090-:9090 \
  -device virtio-net-pci,netdev=net0 \
  -serial "unix:$vm_dir/iso-serial.sock,server=on,wait=off" \
  -qmp "unix:$vm_dir/iso-qmp.sock,server=on,wait=off" >vm-results/iso-qemu.log 2>&1 &
qemu_pid=$!
cleanup() {
  status=$?
  python3 - <<'PY' || true
import json, socket
from pathlib import Path
s = socket.socket(socket.AF_UNIX); s.settimeout(5)
s.connect('/tmp/omadora-vm/iso-qmp.sock')
f = s.makefile('rwb'); f.readline()
for command in ({'execute': 'qmp_capabilities'}, {'execute': 'screendump', 'arguments': {'filename': str(Path('vm-results/iso-console.png').resolve()), 'format': 'png'}}):
    f.write((json.dumps(command)+'\n').encode()); f.flush()
    while True:
        response = json.loads(f.readline())
        if 'return' in response or 'error' in response: break
PY
  ssh -i "$vm_dir/key" -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 root@127.0.0.1 'journalctl -b --no-pager' >vm-results/iso-journal.log 2>&1 || true
  kill "$qemu_pid" "$xvfb_pid" 2>/dev/null || true
  wait "$qemu_pid" 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT
python3 tests/fedora-workstation-install.py
# The completed installer has flushed the target filesystems. Power down the
# live environment before the regular acceptance suite boots the installed disk.
ssh -i "$vm_dir/key" -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 'systemctl poweroff' || true
for ((i=0; i<60; i++)); do kill -0 "$qemu_pid" 2>/dev/null || break; sleep 1; done
kill -0 "$qemu_pid" 2>/dev/null && exit 1
trap - EXIT
kill "$xvfb_pid" 2>/dev/null || true
