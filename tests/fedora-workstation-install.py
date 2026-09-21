"""Drive the stock Anaconda Web UI in a disposable, loopback-only ISO VM."""
import json
import os
import re
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
shell_ready = threading.Event()
key = shlex.quote((VM / 'key.pub').read_text().strip())
command = (f"if [ ! -e /etc/initrd-release ]; then mkdir -p /root/.ssh; printf '%s\\n' {key} >/root/.ssh/authorized_keys; "
           "chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys; "
           "restorecon -RF /root/.ssh; echo root:omadora-live-test-only | chpasswd; ssh-keygen -A; "
           "systemctl reset-failed sshd; systemctl start sshd && echo ISO_SSH_READY || journalctl -u sshd -n 20 --no-pager; fi")
def drain_serial():
    # Drain continuously: pausing reads around slow SSH probes backpressures
    # QEMU's emulated UART and can stall each kernel/systemd console write.
    with (OUT / 'iso-console.log').open('wb') as log:
        recent = b''
        while True:
            try:
                data = serial.recv(65536)
                if not data:
                    return
                log.write(data); log.flush()
                recent = (recent + data)[-8192:]
                # USB boots pass through GRUB first. Sending our shell script
                # there interrupts its countdown and opens its command prompt.
                if re.search(rb'(?:sh-[0-9.]+|\[root@[^\r\n]+\])#\s', recent):
                    shell_ready.set()
            except socket.timeout:
                continue
            except OSError:
                return


threading.Thread(target=drain_serial, daemon=True).start()
if os.environ.get('OMADORA_CUSTOM_ISO'):
    assert shell_ready.wait(300), 'Installer debug shell prompt did not appear after USB boot'
    deadline = time.monotonic() + 180
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
if os.environ.get('OMADORA_CUSTOM_ISO'):
    guest("test -f /etc/anaconda/profile.d/omadora.conf && grep -qx 'Product=Omadora' /.buildstamp")
# SSH can become ready before GNOME exports DISPLAY. Anaconda's browser exits
# immediately when that variable is absent, taking its backend down with it.
if not os.environ.get('OMADORA_CUSTOM_ISO'):
    deadline = time.monotonic() + 180
    while True:
        session_env = dict(line.split('=', 1) for line in guest(
            'runuser -u liveuser -- env XDG_RUNTIME_DIR=/run/user/1000 '
            'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus '
            'systemctl --user show-environment 2>/dev/null || true').splitlines() if '=' in line)
        if session_env.get('DISPLAY') and session_env.get('WAYLAND_DISPLAY'):
            break
        assert time.monotonic() < deadline, 'Live GNOME display environment unavailable'
        time.sleep(2)
    display_env = ' '.join(shlex.quote(key + '=' + session_env[key]) for key in
                           ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY') if session_env.get(key))
    guest('nohup env PKEXEC_UID=1000 ' + display_env + ' liveinst >/tmp/omadora-liveinst.log 2>&1 </dev/null &')
# Fedora 44 liveinst serves the local installer over HTTP on guest loopback:80.
# Tunnel that existing service rather than depending on newer remote boot flags.
tunnel = subprocess.Popen(SSH[:-1] + ['-N', '-o', 'ExitOnForwardFailure=yes',
                                    '-L', '127.0.0.1:9080:127.0.0.1:80', SSH[-1]],
                          stdout=subprocess.DEVNULL, stderr=(OUT / 'iso-tunnel.log').open('w'))

# The HTTP service starts before Anaconda's DBus modules. Follow the same
# readiness point as liveinst's own browser launch, avoiding a half-built UI.
deadline = time.monotonic() + 180
while True:
    ready = guest("grep -c 'web-ui: starting cockpit web view' /tmp/anaconda.log 2>/dev/null || true").strip()
    if ready.isdigit() and int(ready) > 0:
        break
    assert time.monotonic() < deadline, 'Anaconda backend initialization timed out'
    time.sleep(3)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(ignore_https_errors=True, viewport={'width': 1440, 'height': 1000})
    browser_log = (OUT / 'iso-browser.log').open('w')
    page.on('console', lambda message: (browser_log.write(f'{message.type}: {message.text}\n'), browser_log.flush()))
    page.on('pageerror', lambda error: (browser_log.write(f'PAGE ERROR: {error}\n'), browser_log.flush()))
    page.set_default_timeout(30000)
    try:
        deadline = time.monotonic() + 240
        while True:
            try:
                assert tunnel.poll() is None, 'Installer SSH tunnel exited'
                page.goto('http://127.0.0.1:9080/cockpit/@localhost/anaconda-webui/index.html', timeout=15000)
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(5)
        page.locator('#installation-next-btn').wait_for(state='visible', timeout=180000)
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
            timezone = frame.locator('#anaconda-screen-date-time-region-toggle')
            if timezone.is_visible():
                automatic = frame.locator('#anaconda-screen-date-time-auto-timezone')
                if automatic.is_visible():
                    automatic.uncheck()
                timezone.click()
                frame.locator('#anaconda-screen-date-time-region').get_by_role('option', name='America', exact=True).click()
                frame.locator('#anaconda-screen-date-time-city-toggle').click()
                frame.locator('#anaconda-screen-date-time-city').get_by_role('option', name=re.compile(r'^New[ _]York$')).click()
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
            if frame.locator('.anaconda-screen-progress-status-success').is_visible():
                break
            if frame.locator('#critical-error-bz-report-modal').is_visible() or 'Installation failed' in text:
                raise RuntimeError(text)
            (OUT / 'iso-progress.txt').write_text(text)
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
        browser_log.close()
        tunnel.terminate()

# Anaconda installed the disk. Add only the CI access settings needed by the
# existing acceptance suite, not a replacement desktop environment or kernel.
account_setup = ('chroot "$target" id omadora-test' if os.environ.get('OMADORA_CUSTOM_ISO') else
                 'chroot "$target" id omadora-test || chroot "$target" useradd -m -G wheel omadora-test')
admin_check = ('chroot "$target" id -nG omadora-test | tr " " "\\n" | grep -qx wheel'
               if os.environ.get('OMADORA_CUSTOM_ISO') else '')
password_setup = '' if os.environ.get('OMADORA_CUSTOM_ISO') else 'echo omadora-test:omadora-vm-test-only | chroot "$target" chpasswd'
script = f'''
set -eu
target=/mnt/sysroot
test -f "$target/etc/fedora-release"
cat "$target/etc/os-release"
chroot "$target" rpm -qa | sort >/tmp/iso-installed-packages.txt
{account_setup}
{admin_check}
{password_setup}
install -d -m700 "$target/home/omadora-test/.ssh"
printf '%s\\n' {key} >"$target/home/omadora-test/.ssh/authorized_keys"
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
    'image': 'Omadora-44-x86_64.iso' if os.environ.get('OMADORA_CUSTOM_ISO') else 'Fedora-Workstation-Live-44-1.7.x86_64.iso',
    'installer': 'unmodified Anaconda Web UI', 'firmware': 'UEFI',
    'test_instrumentation': ['loopback SSH tunnel to local installer', 'live-only serial debug shell/firstboot mask',
                             'ephemeral SSH key', 'test user/password', 'test sudo rule'],
    'desktop_added_by_dnf': False,
}, indent=2))
print('PASS: ISO installed through Anaconda', flush=True)
