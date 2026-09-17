"""Independent disposable VM: portal, network, virtual sound, GNOME, recovery."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location('interactions', Path(__file__).with_name('fedora-vm-interactions.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def portal():
    with (v.OUT / 'portal.log').open('w') as log:
        p = subprocess.Popen(v.ssh + ["bash -c 'source ~/source/tests/vm-session.sh; python3 ~/source/tests/portal-chooser.py'"], stdout=log, stderr=log)
        v.wait_for(lambda: any('Omadora portal test' in c['title'] for c in json.loads(v.guest('hyprctl clients -j'))))
        v.guest('grim /tmp/omadora-vm-results/portal.png')
        v.keys('esc')
        assert p.wait(timeout=30) == 0
    return 'File chooser displayed through xdg-desktop-portal and returned cancellation.'


def network():
    v.qmp('set_link', {'name': 'net0', 'up': False})
    time.sleep(4)
    v.qmp('set_link', {'name': 'net0', 'up': True})
    v.wait_for(lambda: v.guest('curl -fsI --max-time 10 https://fedoraproject.org >/dev/null; echo online') == 'online', 60)
    return v.guest('nmcli -t -f DEVICE,STATE device')


def sound():
    # Verify the PipeWire graph exposes the emulated HDA output. It cannot
    # establish sound quality or physical speakers/headphone routing.
    detail = v.guest('wpctl status; pactl list short sinks')
    assert 'alsa_output' in detail, detail
    v.guest('wpctl set-mute @DEFAULT_AUDIO_SINK@ 1; wpctl get-volume @DEFAULT_AUDIO_SINK@ | grep MUTED')
    v.guest('wpctl set-mute @DEFAULT_AUDIO_SINK@ 0; wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.4')
    return detail


def notifications():
    v.guest("notify-send -t 10000 'Omadora test' 'Notification service smoke test'")
    time.sleep(1)
    v.guest('grim /tmp/omadora-vm-results/notification.png')
    return 'Notification request accepted; screenshot saved for visual inspection.'


def raw(command, timeout=90):
    p = subprocess.run(v.ssh + [command], text=True, capture_output=True, timeout=timeout)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout.strip()


def recovery():
    raw("printf '[User]\\nXSession=gnome\\nSession=gnome\\nSystemAccount=false\\n' | sudo tee /var/lib/AccountsService/users/omadora-test >/dev/null; sudo systemctl restart gdm")
    v.wait_for(lambda: raw('pgrep -u $(id -u) -x gnome-shell'), 90)
    # No Hyprland environment is supplied to restore-config from this SSH/TTY.
    result = raw("omadora restore-config \"$(python3 -c 'import json,pathlib; print(json.loads((pathlib.Path.home()/\".local/state/omadora/installation.json\").read_text())[\"backup\"])')\"")
    assert raw('cat ~/.config/hypr/original-test-marker') == 'pre-install sentinel'
    assert raw('cat ~/.local/state/omadora/backups/before-restore-*/.config/hypr/post-install-marker') == 'post-install sentinel'
    raw('test ! -e ~/.config/hypr/post-install-marker; pgrep -u $(id -u) -x gnome-shell')
    return result + '; GNOME remained running and later edits were rescued.'


v.check('portal file chooser', portal)
v.check('network reconnect', network)
v.check('virtual audio controls', sound)
v.check('notifications', notifications)
v.check('GNOME and config recovery', recovery)
assert all(r['status'] == 'PASS' for r in v.results), v.results
