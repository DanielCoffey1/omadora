"""Booted KDE fixture: Omadora, Plasma and return to Plasma Login Manager.

Only the disposable guest's autologin configuration is changed. This is not
a fresh KDE ISO or physical GPU test. Screenshots are retained for inspection.
"""
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import time

spec = importlib.util.spec_from_file_location('interactions', Path(__file__).with_name('fedora-vm-interactions.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
MANAGER = os.environ.get('VM_LOGIN_MANAGER', 'sddm')
assert MANAGER in ('sddm', 'plasmalogin')
CONFIG = '/etc/sddm.conf.d/zz-omadora-test.conf' if MANAGER == 'sddm' else '/etc/plasmalogin.conf'
GREETER = '[s]ddm-greeter' if MANAGER == 'sddm' else '[p]lasma-login-greeter'


def raw(command, timeout=90):
    result = subprocess.run(v.ssh + ['bash -c ' + shlex.quote(command)], text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(command + ': ' + result.stdout + result.stderr)
    return result.stdout.strip()


def screenshot(name):
    # QMP captures the actual virtual display, including the login greeter.
    v.qmp('screendump', {'filename': str((v.OUT / (name + '.ppm')).resolve())})


def wait_process(name, present=True):
    def ready():
        found = raw('pgrep -u $(id -u) -x ' + name + ' >/dev/null && echo yes || echo no') == 'yes'
        return found == present
    v.wait_for(ready, 120)


def logout(name):
    sessions = raw("loginctl list-sessions --no-legend | awk '$3 == \"omadora-test\" {print $1}'").splitlines()
    # Each SSH invocation has its own short-lived logind session; it may have
    # vanished by the next invocation. Ignore those, but require one Wayland
    # session belonging to the fixture user.
    graphical = [sid for sid in sessions if raw('loginctl show-session ' + shlex.quote(sid) + ' -p Type --value 2>/dev/null || true') == 'wayland']
    assert len(graphical) == 1, graphical
    if name == 'plasmashell':
        raw('export XDG_RUNTIME_DIR=/run/user/$(id -u); export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus; gdbus call --session --dest org.kde.Shutdown --object-path /Shutdown --method org.kde.Shutdown.logout')
    else:
        v.guest('omarchy-system-logout')
    wait_process(name, False)
    v.wait_for(lambda: raw('pgrep -f "' + GREETER + '" >/dev/null && echo ready || true') == 'ready', 90)
    time.sleep(10)
    raw('systemctl is-active ' + MANAGER + ' | grep -x active')
    screenshot(name + '-logout-greeter')


def plasma_roundtrip():
    # Autologin is configured only to make session startup deterministic in CI.
    raw("printf '[Autologin]\nUser=omadora-test\nSession=plasma.desktop\nRelogin=false\n' | sudo tee " + CONFIG + " >/dev/null; sudo systemctl restart " + MANAGER)
    wait_process('plasmashell')
    time.sleep(15)
    screenshot('plasma-desktop')
    logout('plasmashell')
    return 'Plasma started through the selected login manager and returned to a running greeter; inspect screenshots.'


def repeated_authentication():
    for _ in range(2):
        v.authentication()
    return 'Two lock cycles: wrong passwords rejected and correct password unlocked shell and compositor.'


def greeter_authentication():
    if MANAGER != 'sddm':
        return 'SDDM password test applies to the default KDE login manager.'
    raw('sudo systemctl stop sddm; sudo rm -f ' + CONFIG)
    raw("state_home=$(getent passwd sddm | cut -d: -f6); sudo mkdir -p \"$state_home\"; printf '[Last]\\nUser=omadora-test\\nSession=/usr/share/wayland-sessions/omadora.desktop\\n' | sudo tee \"$state_home/state.conf\" >/dev/null; sudo chown sddm:sddm \"$state_home/state.conf\"; sudo systemctl start sddm")
    v.wait_for(lambda: raw('pgrep -f "' + GREETER + '" >/dev/null && echo ready || true') == 'ready', 90)
    time.sleep(15)
    screenshot('sddm-password-login')
    v.type_password('incorrect')
    time.sleep(10)
    assert raw('pgrep -u $(id -u) -x Hyprland >/dev/null && echo yes || echo no') == 'no', 'Wrong login password started a desktop'
    screenshot('sddm-wrong-password')
    v.type_password('omadora-vm-test-only')
    try:
        wait_process('Hyprland')
        v.wait_for(lambda: not v.lock_status()['locked'], 90)
        assert '/usr/local/bin/omadora-session' in raw("sudo journalctl -b -u sddm --no-pager | grep 'Starting Wayland user session:' | tail -1"), 'Login did not select Omadora'
        v.keys('meta_l', 'ret')
        v.wait_for(lambda: 'foot' in v.guest('hyprctl clients -j'), 30)
        time.sleep(10)
    finally:
        screenshot('sddm-correct-password')
    return 'Real SDDM password login: wrong password rejected; correct password started Omadora without autologin.'


v.check('password authentication', repeated_authentication)
v.check('keyboard and windows', v.keyboard_windows)
v.check('clipboard', v.clipboard)
v.check('power profiles', v.power)
v.check('theme switching', v.themes)
v.check('Omadora logout to KDE greeter', lambda: logout('Hyprland') or 'Session ended and greeter process returned; screenshot retained.')
v.check('Plasma login and logout to greeter', plasma_roundtrip)
v.check('SDDM password login', greeter_authentication)
(v.OUT / 'kde-login-journal.log').write_text(raw('sudo journalctl -b -u ' + MANAGER + ' --no-pager'))
assert all(result['status'] == 'PASS' for result in v.results), v.results
