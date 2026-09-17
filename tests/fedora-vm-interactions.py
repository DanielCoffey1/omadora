"""Host-side acceptance checks. Only controls the disposable QEMU guest.

Keyboard input goes through QMP, including password authentication; no test-only
unlock API is added to the desktop. See QEMU's QMP send-key documentation.
"""
import json
from pathlib import Path
import shlex
import socket
import subprocess
import time
import traceback

OUT = Path('vm-results')
results = []
ssh = ['ssh', '-i', '/tmp/omadora-vm/key', '-p', '2222', '-o',
       'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
       '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes', 'omadora-test@127.0.0.1']


def guest(command, timeout=45):
    script = 'source ~/source/tests/vm-session.sh; ' + command
    p = subprocess.run(ssh + ['bash -c ' + shlex.quote(script)],
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'{command}: {p.stdout[-2000:]} {p.stderr[-2000:]}')
    return p.stdout.strip()


sock = socket.socket(socket.AF_UNIX)
sock.settimeout(15)
sock.connect('/tmp/omadora-vm/qmp.sock')
stream = sock.makefile('rwb')
json.loads(stream.readline())


def qmp(command, arguments=None):
    stream.write((json.dumps({'execute': command, 'arguments': arguments or {}}) + '\n').encode())
    stream.flush()
    while True:
        response = json.loads(stream.readline())
        if 'error' in response:
            raise RuntimeError(response)
        if 'return' in response:
            return response['return']


qmp('qmp_capabilities')


def keys(*codes):
    qmp('send-key', {'keys': [{'type': 'qcode', 'data': c} for c in codes], 'hold-time': 80})
    time.sleep(.15)


def type_password(value):
    keys('ctrl', 'a')
    keys('backspace')
    for char in value:
        keys('minus' if char == '-' else char)
    keys('ret')


def wait_for(predicate, seconds=40):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        time.sleep(2)
    raise AssertionError('Condition did not become true before timeout')


def check(name, action):
    try:
        detail = action()
        record = {'test': name, 'status': 'PASS', 'detail': detail}
    except Exception as error:
        record = {'test': name, 'status': 'FAIL', 'detail': repr(error), 'traceback': traceback.format_exc()}
    results.append(record)
    print(json.dumps(record), flush=True)
    (OUT / 'interactions.json').write_text(json.dumps(results, indent=2))


def lock_status():
    return json.loads(guest('omarchy-shell lock status'))


def unlock():
    type_password('omadora-vm-test-only')
    wait_for(lambda: not lock_status()['locked'])
    assert guest('omarchy-hyprland-session-locked; echo $?').endswith('1')


def authentication():
    assert guest('omarchy-shell lock lock') == 'ok'
    wait_for(lambda: lock_status()['secure'])
    # Two real failed attempts must leave both client and compositor locked.
    for _ in range(2):
        type_password('incorrect')
        time.sleep(5)
        assert lock_status()['secure']
        guest('omarchy-hyprland-session-locked')
    unlock()
    return 'Two wrong passwords rejected; correct password unlocked the compositor.'


def keyboard_windows():
    keys('meta_l', 'ret')
    wait_for(lambda: any(c['class'] == 'foot' for c in json.loads(guest('hyprctl clients -j'))))
    keys('meta_l', '2')
    wait_for(lambda: json.loads(guest('hyprctl activeworkspace -j'))['id'] == 2)
    keys('meta_l', '1')
    keys('meta_l', 't')
    wait_for(lambda: json.loads(guest('hyprctl activewindow -j'))['floating'])
    keys('meta_l', 'w')
    return 'Super+Return terminal, workspace switching, floating and closing.'


def clipboard():
    value = guest("printf 'Omadora clipboard test' | wl-copy >/dev/null 2>&1; wl-paste --no-newline")
    assert value == 'Omadora clipboard test', value
    return value


def power():
    def set_profile(profile):
        # Execute through the desktop's user manager, not an inactive SSH
        # logind session, so normal active-session polkit policy applies.
        guest('systemd-run --user --wait --pipe /usr/local/share/omadora/bin/powerprofilesctl set ' + profile)
    original = guest('powerprofilesctl get')
    try:
        for profile in ('power-saver', 'balanced', 'performance'):
            set_profile(profile)
            assert guest('powerprofilesctl get') == profile
    finally:
        set_profile(original)
    return 'All three profiles set, read back, and original restored.'


def themes():
    for theme in ('catppuccin', 'white', 'tokyo-night'):
        guest('omarchy-theme-set ' + theme, timeout=100)
        time.sleep(4)
        assert guest('hyprctl configerrors') in ('', 'ok')
        assert guest('omarchy-shell shell ping') == 'ok'
        expected = 'prefer-light' if theme == 'white' else 'prefer-dark'
        assert expected in guest('gsettings get org.gnome.desktop.interface color-scheme')
        guest(f'grim /tmp/omadora-vm-results/theme-{theme}.png')
    return 'Dark/light/dark themes updated shell and GTK color scheme without compositor config errors.'


def suspend():
    # Suspend the actual guest OS, not merely the hypervisor.
    guest('omarchy-shell lock lock')
    wait_for(lambda: lock_status()['secure'])
    process = subprocess.Popen(ssh + ['sudo systemctl suspend'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_for(lambda: qmp('query-status')['status'] == 'suspended', seconds=60)
    time.sleep(3)
    qmp('system_wakeup')
    wait_for(lambda: lock_status()['secure'], seconds=60)
    process.wait(timeout=30)
    unlock()
    assert guest('omarchy-shell shell ping') == 'ok'
    return 'Guest entered ACPI suspend, resumed, remained locked, and accepted password.'


if __name__ == '__main__':
    check('password authentication', authentication)
    check('keyboard and windows', keyboard_windows)
    check('clipboard', clipboard)
    check('power profiles', power)
    check('theme switching', themes)
    check('suspend/resume', suspend)
    print('Interaction tests complete.', flush=True)
# Caller continues with app tests even when an individual interaction fails.
