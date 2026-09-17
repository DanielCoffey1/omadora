#!/bin/bash
# Disposable CI VM: official Fedora Cloud image + Workstation environment.
# Test credentials and autologin exist only inside this ephemeral VM.
set -euo pipefail
mkdir -p vm-results /tmp/omadora-vm
exec > >(tee vm-results/host.log) 2>&1
task_root=$PWD
vm_dir=/tmp/omadora-vm
image=Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2
base=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images
curl -fL --retry 3 "$base/$image" -o "$vm_dir/disk.qcow2"
curl -fL --retry 3 "$base/Fedora-Cloud-44-1.7-x86_64-CHECKSUM" -o "$vm_dir/CHECKSUM"
expected=$(sed -n "s/^SHA256 ($image) = //p" "$vm_dir/CHECKSUM")
[[ $expected =~ ^[0-9a-f]{64}$ ]]
printf '%s  %s\n' "$expected" "$vm_dir/disk.qcow2" | sha256sum -c -
qemu-img resize "$vm_dir/disk.qcow2" 30G
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
accel=tcg
if [[ -e /dev/kvm ]]; then sudo chmod 0666 /dev/kvm; accel=kvm; fi
echo "VM acceleration: $accel"
Xvfb :99 -screen 0 1920x1080x24 >vm-results/xvfb.log 2>&1 &
xvfb_pid=$!
export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1
qemu-system-x86_64 -accel "$accel" -m 4096 -smp 2 \
  -drive "file=$vm_dir/disk.qcow2,if=virtio,format=qcow2" \
  -drive "file=$vm_dir/seed.img,format=raw,if=virtio" \
  -device virtio-vga-gl -display gtk,gl=on \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=net0 \
  -serial "file:$task_root/vm-results/serial.log" \
  -qmp "unix:$vm_dir/qmp.sock,server=on,wait=off" >vm-results/qemu.log 2>&1 &
qemu_pid=$!
cleanup() {
  status=$?
  ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'sudo journalctl -b --no-pager -n 1000' >vm-results/guest-journal.log 2>&1 || true
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
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'sudo cloud-init status --wait --format json >/tmp/cloud-status.json; cat /tmp/cloud-status.json; python3 -c '\''import json; s=json.load(open("/tmp/cloud-status.json")); assert s["status"] == "done" and not s.get("errors"), s'\'''
tar --exclude=.git --exclude=__pycache__ -czf "$vm_dir/source.tar.gz" omadora.py apps.json upstream.lock.json packages assets tests
scp -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$vm_dir/source.tar.gz" omadora-test@127.0.0.1:/tmp/source.tar.gz
ssh "${ssh_options[@]}" omadora-test@127.0.0.1 'bash -s' <<'GUEST'
set -euo pipefail
sudo dnf install -y --allowerasing @workstation-product-environment fedora-release-identity-workstation
mkdir -p ~/source
tar -xzf /tmp/source.tar.gz -C ~/source
cd ~/source
python3 omadora.py install
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
scp -r -i "$vm_dir/key" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null omadora-test@127.0.0.1:/tmp/omadora-vm-results/. vm-results/
echo 'PASS: booted Fedora VM, GDM autologin, Hyprland, Quickshell IPC and screenshots.'
