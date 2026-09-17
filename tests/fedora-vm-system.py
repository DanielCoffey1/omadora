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
    v.guest("printf 'Omadora portal fixture' >/tmp/omadora-portal.txt")
    (v.OUT / 'gtk-rendered-theme.log').write_text(v.guest('python3 ~/source/tests/gtk-theme-probe.py dark'))
    (v.OUT / 'gtk-settings.log').write_text(v.guest('''python3 - <<'PY'
import gi, os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
Gtk.init([])
settings = Gtk.Settings.get_default()
print('display', Gdk.Display.get_default().__class__.__name__)
for key in ('gtk-theme-name', 'gtk-icon-theme-name', 'gtk-application-prefer-dark-theme'):
    print(key, settings.get_property(key))
PY
systemctl --user show-environment | grep -E '^(GDK_BACKEND|GTK_THEME|XDG_CURRENT_DESKTOP|WAYLAND_DISPLAY|DISPLAY)='
gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.Settings.Read org.gnome.desktop.interface gtk-theme
'''))
    with (v.OUT / 'portal.log').open('w') as log:
        p = subprocess.Popen(v.ssh + ["bash -c 'source ~/source/tests/vm-session.sh; python3 ~/source/tests/portal-chooser.py'"], stdout=log, stderr=log)
        v.wait_for(lambda: any('Omadora portal test' in c['title'] for c in json.loads(v.guest('hyprctl clients -j'))))
        (v.OUT / 'portal-windows.json').write_text(v.guest('hyprctl clients -j'))
        v.guest('grim /tmp/omadora-vm-results/portal.png')
        v.keys('ctrl', 'l')
        for char in '/tmp/omadora-portal.txt':
            v.keys({'/': 'slash', '-': 'minus', '.': 'dot'}.get(char, char))
        v.keys('ret')
        time.sleep(2)
        if p.poll() is None:
            v.keys('ret')
        assert p.wait(timeout=30) == 0
    return 'File chooser displayed and returned the selected fixture file URI.'


def network():
    v.qmp('set_link', {'name': 'net0', 'up': False})
    time.sleep(4)
    v.qmp('set_link', {'name': 'net0', 'up': True})
    v.wait_for(lambda: v.guest('curl -fsI --max-time 10 https://fedoraproject.org >/dev/null && echo online') == 'online', 60)
    return v.guest('nmcli -t -f DEVICE,STATE device')


def sound():
    # Verify the PipeWire graph exposes the emulated HDA output. It cannot
    # establish sound quality or physical speakers/headphone routing.
    detail = v.guest('wpctl status; pactl list short sinks')
    assert 'alsa_output' in detail, detail
    v.guest('wpctl set-mute @DEFAULT_AUDIO_SINK@ 1; wpctl get-volume @DEFAULT_AUDIO_SINK@ | grep MUTED')
    v.guest('wpctl set-mute @DEFAULT_AUDIO_SINK@ 0; wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.4')
    v.guest('omarchy-audio-output-volume raise; pactl get-sink-volume @DEFAULT_SINK@ | grep "45%"')
    v.guest('omarchy-audio-output-volume mute-toggle; pactl get-sink-mute @DEFAULT_SINK@ | grep yes')
    time.sleep(.3)
    v.guest('omarchy-audio-output-volume mute-toggle; pactl get-sink-mute @DEFAULT_SINK@ | grep no')
    action = v.guest("python3 -c 'import json; print(json.load(open(\"/usr/local/share/omadora/upstream/default/omarchy/omarchy-menu.jsonc\"))[\"setup.audio\"][\"action\"])'")
    assert v.guest(action) == ''  # toggle is a void IPC method
    time.sleep(2)
    v.guest('grim /tmp/omadora-vm-results/audio-panel.png')
    v.guest('omarchy-shell shell hide omarchy.audio')
    return detail


def notifications():
    v.guest("notify-send -t 10000 'Omadora test' 'Notification service smoke test'")
    time.sleep(1)
    v.guest('grim /tmp/omadora-vm-results/notification.png')
    return 'Notification request accepted; screenshot saved for visual inspection.'


def raw(command, timeout=90):
    p = subprocess.run(v.ssh + [command], text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(command + ': ' + p.stdout + p.stderr)
    return p.stdout.strip()


def recovery():
    raw("sudo systemctl stop gdm; sudo systemctl stop accounts-daemon; printf '[User]\\nXSession=gnome\\nSession=gnome\\nSystemAccount=false\\n' | sudo tee /var/lib/AccountsService/users/omadora-test >/dev/null; sudo systemctl start accounts-daemon gdm")
    v.wait_for(lambda: raw('pgrep -u $(id -u) -x gnome-shell'), 90)
    # No Hyprland environment is supplied to restore-config from this SSH/TTY.
    result = raw("omadora restore-config \"$(python3 -c 'import json,pathlib; print(json.loads((pathlib.Path.home()/\".local/state/omadora/installation.json\").read_text())[\"backup\"])')\"")
    assert raw('cat ~/.config/hypr/original-test-marker') == 'pre-install sentinel'
    assert raw('cat ~/.local/state/omadora/backups/before-restore-*/.config/hypr/post-install-marker') == 'post-install sentinel'
    raw('test ! -e ~/.config/hypr/post-install-marker; pgrep -u $(id -u) -x gnome-shell')
    raw('test ! -e ~/.config/fontconfig/conf.d/99-omadora.conf')
    original = raw("python3 -c 'import json,pathlib; p=pathlib.Path.home()/\".local/state/omadora/installation.json\"; b=pathlib.Path(json.loads(p.read_text())[\"backup\"]); print(json.dumps(json.loads((b/\"desktop-settings.json\").read_text())))'")
    import json
    for key, expected in json.loads(original).items():
        assert raw('gsettings get org.gnome.desktop.interface ' + key) == expected
    return result + '; GNOME remained running and later edits were rescued.'


def desktop_shortcuts():
    v.keys('meta_l', 'ctrl', 't')
    v.wait_for(lambda: 'top' in v.guest('pgrep -a -x top'))
    window = json.loads(v.guest('hyprctl activewindow -j'))
    assert v.guest(f'readlink /proc/{int(window["pid"])}/exe').endswith('/foot')
    v.keys('q')
    v.wait_for(lambda: v.guest('pgrep -x top >/dev/null; echo $?') == '1')
    return 'Activity shortcut opened top in Foot and quit normally.'


def screenshot_keyboard():
    v.guest('mkdir -p /tmp/omadora-screenshots')
    command = 'source ~/source/tests/vm-session.sh; OMARCHY_SCREENSHOT_DIR=/tmp/omadora-screenshots omarchy-capture-screenshot'
    def capture():
        return subprocess.Popen(v.ssh + ['bash -c ' + __import__('shlex').quote(command)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    process = capture()
    v.wait_for(lambda: v.guest('pgrep -x slurp'))
    time.sleep(1)
    v.keys('esc')
    assert process.wait(30) == 0
    assert v.guest('find /tmp/omadora-screenshots -type f | wc -l') == '0'
    v.wait_for(lambda: v.guest('pgrep -x hyprpicker >/dev/null; echo $?') == '1')
    process = capture()
    v.wait_for(lambda: v.guest('pgrep -x slurp'))
    time.sleep(1)
    v.keys('ctrl', 'ret')
    assert process.wait(30) == 0
    assert v.guest('find /tmp/omadora-screenshots -name "*.png" | wc -l') == '1'
    v.guest('wl-paste --type image/png > /tmp/omadora-vm-results/screenshot-clipboard.png; cmp /tmp/omadora-screenshots/*.png /tmp/omadora-vm-results/screenshot-clipboard.png')
    v.wait_for(lambda: v.guest('pgrep -x hyprpicker >/dev/null; echo $?') == '1')
    return 'Escape canceled without saving; Ctrl+Enter captured fullscreen; saved PNG and clipboard match; overlays cleaned up.'


v.check('Activity shortcut', desktop_shortcuts)
v.check('screenshot keyboard and clipboard', screenshot_keyboard)
v.check('portal file chooser', portal)
v.check('network reconnect', network)
v.check('virtual audio controls', sound)
v.check('notifications', notifications)
v.check('GNOME and config recovery', recovery)
assert all(r['status'] == 'PASS' for r in v.results), v.results
