"""Repeated GDM handoffs and real S3 cycles in the disposable CI VM."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import time

t = runpy.run_path('tests/fedora-vm-interactions.py')
guest, wait_for, check = (t[n] for n in ('guest', 'wait_for', 'check'))
out = Path('vm-results')


def raw(command, timeout=30):
    p = subprocess.run(t['ssh'] + [command], capture_output=True, text=True, timeout=timeout)
    return p.stdout + p.stderr


def evidence(label):
    # Do not depend on a responsive compositor to collect failure evidence.
    commands = {
        'processes': 'ps -eo pid,ppid,stat,wchan:40,cmd; loginctl list-sessions; loginctl seat-status seat0',
        'kernel': 'sudo journalctl -k -b --no-pager',
        'journal': 'sudo journalctl -b --no-pager -n 1500',
        'graphics': 'cat /run/user/1000/hypr/*/hyprland.log; cat ~/.cache/hyprland/hyprlandCrashReport*.txt',
        'stacks': "for p in $(pgrep -x Hyprland) $(ps -eo pid=,stat= | awk '$2 ~ /^D/ {print $1}'); do echo PID=$p; sudo cat /proc/$p/stack; done",
        'packages': 'rpm -q hyprland aquamarine mesa-dri-drivers kernel uwsm; cat /usr/share/wayland-sessions/hyprland.desktop',
    }
    for name, command in commands.items():
        try:
            (out / f'{label}-{name}.log').write_text(raw(command))
        except Exception as error:
            (out / f'{label}-{name}.log').write_text(repr(error))
    try:
        t['qmp']('screendump', {'filename': str((out / f'{label}.ppm').resolve())})
    except Exception as error:
        (out / f'{label}-screenshot-error.txt').write_text(repr(error))


def healthy():
    return guest('timeout 5 hyprctl configerrors') in ('', 'ok') and guest('omarchy-shell shell ping') == 'ok'


def login_cycle():
    old = guest('pgrep -x Hyprland')
    raw('sudo systemctl restart gdm', timeout=60)
    wait_for(lambda: guest('pgrep -x Hyprland') != old and healthy(), seconds=90)
    # Prove input and real password authentication after every new session.
    t['authentication']()
    return 'New GDM session, responsive compositor, wrong-password rejection and correct unlock.'


for cycle in range(1, 6):
    check(f'GDM login {cycle}', login_cycle)
    evidence(f'login-{cycle}')
    if t['results'][-1]['status'] != 'PASS':
        break

if os.environ.get('VM_SLEEP_DIAGNOSTIC') != 'startup-race' and all(r['status'] == 'PASS' for r in t['results']):
    for cycle in range(1, 4):
        check(f'S3 suspend {cycle}', t['suspend'])
        evidence(f'suspend-{cycle}')
        if t['results'][-1]['status'] != 'PASS':
            break

print(json.dumps(t['results'], indent=2), flush=True)
