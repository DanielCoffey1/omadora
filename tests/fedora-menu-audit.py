"""Read-only runtime checks of the installed menu and its infrastructure.

Run inside the disposable Fedora desktop session. Hardware predicates can be
false; a false predicate is not evidence that the hardware action works.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path('/usr/local/share/omadora')
menu = json.loads((root / 'upstream/default/omarchy/omarchy-menu.jsonc').read_text())
# Reviewed dependencies of retained helpers, including indirect launchers.
commands = '''bash awk sed grep find sort cut tr head tail xargs timeout flock
stat readlink realpath mktemp cmp dd df findmnt lsblk ip ping iw nmcli rfkill
bluetoothctl eject lua python3 foot nvim firefox nautilus hyprctl Hyprland
quickshell hyprpicker hyprsunset uwsm-app grim slurp wl-copy wl-paste
wpctl pactl pamixer playerctl brightnessctl ddcutil powerprofilesctl notify-send
gsettings gdbus xdg-open xdg-mime xkbcli fc-list fc-match fc-cache magick
jq curl rpm dnf flatpak top pkill pgrep systemctl loginctl setsid'''.split()
missing = [c for c in commands if not shutil.which(c)]
assert not missing, missing
subprocess.run(['python3', '-c', 'from gi.repository import Gio, GLib'], check=True)
report = {'commands': commands, 'entries': []}
for key, entry in menu.items():
    record = {'id': key, 'entry': entry, 'predicates': {}}
    visible = True
    for field in ('when', 'disabled', 'checked'):
        command = entry.get(field)
        if not command:
            continue
        p = subprocess.run(['bash', '-c', command], capture_output=True, text=True, timeout=20)
        record['predicates'][field] = {'status': p.returncode, 'stderr': p.stderr}
        assert p.returncode in (0, 1), (key, field, p.returncode, p.stderr)
        assert 'command not found' not in p.stderr, (key, field, p.stderr)
        if field == 'when':
            visible = p.returncode == 0
    record['visible'] = visible
    report['entries'].append(record)
out = Path(os.environ.get('OMADORA_MENU_REPORT', '/tmp/omadora-vm-results/menu-audit.json'))
out.write_text(json.dumps(report, indent=2))
print(f'{len(menu)} menu entries and {len(commands)} command dependencies checked; hardware predicates recorded separately.')
