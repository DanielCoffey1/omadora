"""Drive the stock Anaconda Web UI in a disposable, loopback-only ISO VM."""
import base64
import json
import shlex
import socket
import subprocess
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path('vm-results')
VM = Path('/tmp/omadora-vm')
SSH = ['ssh', '-i', str(VM / 'key'), '-p', '2222', '-o', 'StrictHostKeyChecking=no',
       '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
       'root@127.0.0.1']


def guest(command):
    return subprocess.check_output(SSH + [command], text=True, timeout=120)


# A debug shell is enabled only for this live boot. It is not written to the
# installed kernel command line. The public SSH key is disposable test access.
deadline = time.monotonic() + 180
while not (VM / 'iso-serial.sock').exists():
    assert time.monotonic() < deadline, 'QEMU serial socket unavailable'
    time.sleep(1)
serial = socket.socket(socket.AF_UNIX)
serial.settimeout(2)
serial.connect(str(VM / 'iso-serial.sock'))
key = base64.b64encode((VM / 'key.pub').read_bytes()).decode()
command = (f"if [ ! -e /etc/initrd-release ]; then mkdir -p /root/.ssh; echo {key} | base64 -d >/root/.ssh/authorized_keys; "
           "chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys; "
           "restorecon -RF /root/.ssh; echo root:omadora-live-test-only | chpasswd; systemctl start sshd; echo ISO_SSH_READY; fi")
def drain_serial():
    # Drain continuously: pausing reads around slow SSH probes backpressures
    # QEMU's emulated UART and can stall each kernel/systemd console write.
    with (OUT / 'iso-console.log').open('wb') as log:
        while True:
            try:
                data = serial.recv(65536)
                if not data:
                    return
                log.write(data); log.flush()
            except socket.timeout:
                continue
            except OSError:
                return


threading.Thread(target=drain_serial, daemon=True).start()
while time.monotonic() < deadline:
    # Pace input to the emulated UART, including while boot services are busy.
    payload = ('\n' + command + '\n').encode()
    for offset in range(0, len(payload), 32):
        serial.sendall(payload[offset:offset + 32])
        time.sleep(.02)
    probe = subprocess.run(SSH + ['true'], capture_output=True, text=True)
    (OUT / 'iso-ssh-probe.log').write_text(probe.stderr)
    if probe.returncode == 0:
        break
    time.sleep(3)
else:
    raise RuntimeError('Live ISO debug-shell SSH bootstrap did not finish')
# Keep draining while Anaconda runs so the boot console never blocks the guest.
(OUT / 'iso-baseline.log').write_text(guest('cat /etc/os-release; cat /proc/cmdline; rpm -q anaconda-core anaconda-webui; lsblk -f'))
guest("nohup env PKEXEC_UID=1000 liveinst >/tmp/omadora-liveinst.log 2>&1 </dev/null &")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(ignore_https_errors=True, viewport={'width': 1440, 'height': 1000})
    page.set_default_timeout(30000)
    try:
        deadline = time.monotonic() + 240
        while True:
            try:
                page.goto('https://127.0.0.1:9443/cockpit/@localhost/anaconda-webui/index.html', timeout=15000)
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(5)
        for step in range(20):
            time.sleep(3)
            frame = next((f for f in page.frames if f.locator('#installation-next-btn').count()), page.main_frame)
            text = frame.locator('body').inner_text()
            (OUT / f'iso-step-{step:02}.txt').write_text(text)
            page.screenshot(path=str(OUT / f'iso-step-{step:02}.png'))
            print('INSTALLER STEP', step, text[:1600], flush=True)
            if frame.evaluate('window.location.hash') == '#/anaconda-screen-progress':
                break
            account = frame.locator('#anaconda-screen-accounts-create-account-user-name')
            if account.is_visible():
                frame.locator('#anaconda-screen-accounts-create-account-full-name').fill('Omadora Test')
                account.fill('omadora-test')
                for suffix in ('password-field', 'password-confirm-field'):
                    frame.locator('#anaconda-screen-accounts-create-account-' + suffix).fill('omadora-vm-test-only')
            encryption = frame.locator('#disk-encryption-encrypt-devices')
            if encryption.is_visible():
                encryption.uncheck()
            confirmation = frame.locator('#anaconda-screen-review-next-confirmation-checkbox')
            if confirmation.is_visible():
                confirmation.check()
            frame.locator('#installation-next-btn').click()
        else:
            raise RuntimeError('Installer did not reach installation progress')
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            text = frame.locator('body').inner_text()
            if frame.locator('.anaconda-screen-progress-status-success').count():
                break
            if 'Installation failed' in text:
                raise RuntimeError(text)
            time.sleep(10)
        else:
            raise RuntimeError('Timed out copying Workstation onto the virtual disk')
        page.screenshot(path=str(OUT / 'iso-install-complete.png'))
        (OUT / 'iso-install-complete.txt').write_text(text)
    finally:
        page.screenshot(path=str(OUT / 'iso-last.png'))
        (OUT / 'iso-last.html').write_text(page.content())
        (OUT / 'iso-installer.log').write_text(guest('cat /tmp/omadora-liveinst.log; cat /tmp/anaconda.log 2>/dev/null || true'))
        browser.close()

# Anaconda installed the disk. Add only the CI access settings needed by the
# existing acceptance suite, not a replacement desktop environment or kernel.
script = f'''
set -eu
target=/mnt/sysroot
test -f "$target/etc/fedora-release"
cat "$target/etc/os-release"
chroot "$target" rpm -qa | sort >/tmp/iso-installed-packages.txt
chroot "$target" id omadora-test || chroot "$target" useradd -m -G wheel omadora-test
echo omadora-test:omadora-vm-test-only | chroot "$target" chpasswd
install -d -m700 "$target/home/omadora-test/.ssh"
echo {key} | base64 -d >"$target/home/omadora-test/.ssh/authorized_keys"
chmod 600 "$target/home/omadora-test/.ssh/authorized_keys"
chroot "$target" chown -R omadora-test:omadora-test /home/omadora-test/.ssh
printf 'omadora-test ALL=(ALL) NOPASSWD:ALL\\n' >"$target/etc/sudoers.d/omadora-test"
chmod 440 "$target/etc/sudoers.d/omadora-test"
chroot "$target" systemctl enable sshd
chroot "$target" restorecon -RF /home/omadora-test/.ssh /etc/sudoers.d/omadora-test
sync
'''
print(guest('bash -c ' + shlex.quote(script)), flush=True)
(OUT / 'iso-installed-packages.txt').write_text(guest('cat /tmp/iso-installed-packages.txt'))
(OUT / 'iso-provenance.json').write_text(json.dumps({
    'image': 'Fedora-Workstation-Live-44-1.7.x86_64.iso',
    'installer': 'unmodified Anaconda Web UI', 'firmware': 'UEFI',
    'test_instrumentation': ['loopback-only remote installer', 'ephemeral SSH key', 'test user/password', 'test sudo rule'],
    'desktop_added_by_dnf': False,
}, indent=2))
print('PASS: official Workstation Live ISO installed through Anaconda', flush=True)
