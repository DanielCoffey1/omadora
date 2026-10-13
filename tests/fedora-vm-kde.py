"""Booted KDE fixture: Omadora, Plasma and return to Plasma Login Manager.

Only the disposable guest's autologin configuration is changed. This is not
a fresh KDE ISO or physical GPU test. Screenshots are retained for inspection.
"""
import importlib.util
from pathlib import Path
import shlex
import subprocess
import time

spec = importlib.util.spec_from_file_location('interactions', Path(__file__).with_name('fedora-vm-interactions.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


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
    graphical = [sid for sid in sessions if raw('loginctl show-session ' + shlex.quote(sid) + ' -p Type --value') == 'wayland']
    assert len(graphical) == 1, graphical
    raw('loginctl terminate-session ' + shlex.quote(graphical[0]))
    wait_process(name, False)
    v.wait_for(lambda: raw('pgrep -f "[p]lasma-login-greeter" >/dev/null && echo ready || true') == 'ready', 90)
    time.sleep(10)
    raw('systemctl is-active plasmalogin | grep -x active')
    screenshot(name + '-logout-greeter')


def plasma_roundtrip():
    # Autologin is configured only to make session startup deterministic in CI.
    raw("printf '[Autologin]\nUser=omadora-test\nSession=plasma.desktop\nRelogin=false\n' | sudo tee /etc/plasmalogin.conf >/dev/null; sudo systemctl restart plasmalogin")
    wait_process('plasmashell')
    time.sleep(15)
    screenshot('plasma-desktop')
    logout('plasmashell')
    return 'Plasma started through Plasma Login Manager and returned to a running greeter; inspect screenshots.'


v.check('password authentication', v.authentication)
v.check('keyboard and windows', v.keyboard_windows)
v.check('clipboard', v.clipboard)
v.check('power profiles', v.power)
v.check('theme switching', v.themes)
v.check('Omadora logout to KDE greeter', lambda: logout('Hyprland') or 'Session ended and greeter process returned; screenshot retained.')
v.check('Plasma login and logout to greeter', plasma_roundtrip)
(v.OUT / 'kde-login-journal.log').write_text(raw('sudo journalctl -b -u plasmalogin --no-pager'))
assert all(result['status'] == 'PASS' for result in v.results), v.results
