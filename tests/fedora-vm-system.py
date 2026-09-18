"""Independent disposable VM: portal, network, virtual sound, GNOME, recovery."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import shlex

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
    # wl-copy's clipboard owner keeps stderr open after forking. Redirect in
    # the guest, otherwise SSH waits for that descriptor after capture exits.
    command = ('source ~/source/tests/vm-session.sh; '
               'OMARCHY_SCREENSHOT_DIR=/tmp/omadora-screenshots '
               'omarchy-capture-screenshot > /tmp/omadora-vm-results/capture.log 2>&1')
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


def font_preferences():
    path = '~/.config/fontconfig/fonts.conf'
    # A general, unrelated Fontconfig preference must survive font selection.
    v.guest(f'test ! -e {path}')
    sentinel = '<?xml version="1.0"?><fontconfig><!-- preserved user settings --></fontconfig>'
    import shlex
    v.guest('printf %s ' + shlex.quote(sentinel) + ' > ' + path)
    original = v.guest('omarchy-font-current')
    try:
        for font in ('JetBrains Mono', original):
            v.guest('omarchy-font-set ' + shlex.quote(font), timeout=90)
            v.wait_for(lambda: v.guest('omarchy-shell shell ping') == 'ok')
            assert v.guest('omarchy-font-current') == font
            assert v.guest('cat ' + path) == sentinel
    finally:
        v.guest('rm -f -- ' + path)
    return 'Changed and restored monospace font; general Fontconfig preferences remained unchanged.'


def desktop_lifecycle():
    def switch(session):
        raw("sudo systemctl stop gdm; sudo systemctl stop accounts-daemon; "
            f"printf '[User]\\nXSession={session}\\nSession={session}\\nSystemAccount=false\\n' | "
            "sudo tee /var/lib/AccountsService/users/omadora-test >/dev/null; sudo systemctl start accounts-daemon gdm")
        executable = 'gnome-shell' if session == 'gnome' else 'Hyprland'
        v.wait_for(lambda: raw('pgrep -u $(id -u) -x ' + executable), 90)
        if session == 'omadora':
            v.wait_for(lambda: v.guest('omarchy-shell shell ping') == 'ok', 90)
            assert v.guest('hyprctl configerrors') in ('', 'ok')

    v.guest("printf 'keep my config' > ~/.config/foot/lifecycle-sentinel")
    raw('sudo touch /usr/local/share/omadora/previous-release-marker')
    switch('gnome')
    # A bare SSH shell is deliberately independent of the stopped compositor.
    revision = json.loads(raw('cat /usr/local/share/omadora/release.json'))['revision']
    assert len(revision) == 40 and all(c in '0123456789abcdef' for c in revision)
    raw('omadora upgrade --ref ' + revision, timeout=900)
    raw('test ! -e /usr/local/share/omadora/previous-release-marker')
    switch('omadora')
    v.keys('meta_l', 'ret')
    v.wait_for(lambda: any(c['class'] == 'foot' for c in json.loads(v.guest('hyprctl clients -j'))))
    v.guest('grim /tmp/omadora-vm-results/desktop-after-upgrade.png')
    v.keys('meta_l', 'w')
    switch('gnome')
    raw('omadora rollback', timeout=180)
    raw('test -f /usr/local/share/omadora/previous-release-marker')
    switch('omadora')
    assert v.guest('cat ~/.config/foot/lifecycle-sentinel') == 'keep my config'
    v.guest('grim /tmp/omadora-vm-results/desktop-after-rollback.png')
    return 'Upgraded from GNOME, logged into Omadora and opened Foot; rolled back from GNOME and logged in again; personal edit retained.'


def menu_audit():
    detail = v.guest('python3 ~/source/tests/fedora-menu-audit.py', timeout=180)
    bindings = v.guest('omarchy-menu-keybindings --print', timeout=90)
    (v.OUT / 'keybindings.txt').write_text(bindings)
    for label in ('Terminal', 'Omadora menu', 'Switch to workspace 1', 'Activity'):
        assert label in bindings, label
    assert 'Download Video from Web App' not in bindings
    assert 'Copy URL from Web App' not in bindings
    for route in ('root', 'apps', 'style.font', 'install', 'remove', 'install.gaming', 'system'):
        v.guest('omarchy-menu summon ' + route)
        time.sleep(1)
        v.guest('grim /tmp/omadora-vm-results/menu-' + route.replace('.', '-') + '.png')
        v.guest('omarchy-menu close')
    for panel in ('bluetooth', 'monitor', 'power'):
        v.guest('omarchy-shell shell summon omarchy.' + panel)
        time.sleep(1)
        v.guest('grim /tmp/omadora-vm-results/panel-' + panel + '.png')
        v.guest('omarchy-shell shell hide omarchy.' + panel)
    return detail + ' Keybinding help populated; menu/provider and hardware panel screenshots captured.'


def style_controls():
    original = v.guest('omarchy-theme-current')
    config = json.loads(v.guest('cat ~/.config/omarchy/shell.json'))['bar']
    try:
        themes = v.guest('omarchy-theme-list').splitlines()
        alternate = next(t for t in themes if t.lower() != original.lower())
        for theme in (alternate, original):
            v.guest('omarchy-theme-set ' + shlex.quote(theme), timeout=90)
            v.wait_for(lambda: v.guest('omarchy-shell shell ping') == 'ok')
            assert v.guest('omarchy-theme-current').lower() == theme.lower()
            assert v.guest('hyprctl configerrors') in ('', 'ok')
        background = v.guest('readlink -f ~/.local/state/omarchy/current/background')
        backgrounds = v.guest('find -L ~/.local/state/omarchy/current/theme/backgrounds -type f').splitlines()
        if not backgrounds:
            backgrounds = v.guest('find /usr/local/share/omadora/upstream/themes -path "*/backgrounds/*" -type f').splitlines()
        assert backgrounds
        try:
            for path in (backgrounds[0], background):
                v.guest('omarchy-theme-bg-set ' + shlex.quote(path))
                assert v.guest('readlink -f ~/.local/state/omarchy/current/background') == path
        finally:
            v.guest('omarchy-theme-bg-set ' + shlex.quote(background))
        for position in ('bottom', 'left', 'right', 'top'):
            v.guest('omarchy-bar position ' + position)
            assert json.loads(v.guest('cat ~/.config/omarchy/shell.json'))['bar']['position'] == position
        v.guest('omarchy-bar transparent toggle')
        assert json.loads(v.guest('cat ~/.config/omarchy/shell.json'))['bar']['transparent'] != config['transparent']
        v.guest('grim /tmp/omadora-vm-results/style-controls.png')
    finally:
        v.guest('omarchy-theme-set ' + shlex.quote(original), timeout=90)
        v.guest('omarchy-bar position ' + config['position'])
        v.guest('omarchy-bar transparent ' + str(config['transparent']).lower())
    return 'Changed/restored theme and background with valid compositor config; all four bar positions and transparency persisted.'


def desktop_toggles():
    def status(command):
        return json.loads(v.guest(command))
    for command in ('omarchy-toggle-idle', 'omarchy-toggle-nightlight'):
        before = status(command + ' --status')['enabled']
        try:
            v.guest(command + ' >/tmp/omadora-vm-results/toggle.log 2>&1')
            assert status(command + ' --status')['enabled'] != before, command
        finally:
            if status(command + ' --status')['enabled'] != before:
                v.guest(command + ' >/tmp/omadora-vm-results/toggle.log 2>&1')
        assert status(command + ' --status')['enabled'] == before
    for command, marker in (
        ('omarchy-toggle-screensaver', 'screensaver-off'),
        ('omarchy-toggle-bar', 'bar-off'),
        ('omarchy-hyprland-window-gaps-toggle', 'hypr/window-no-gaps.lua'),
    ):
        query = 'test -e ~/.local/state/omarchy/toggles/' + marker + '; echo $?'
        before = v.guest(query)
        try:
            v.guest(command)
            assert v.guest(query) != before, command
        finally:
            if v.guest(query) != before:
                v.guest(command)
        assert v.guest(query) == before
    before = json.loads(v.guest('hyprctl activeworkspace -j'))['tiledLayout']
    try:
        v.guest('omarchy-hyprland-workspace-layout-toggle')
        assert json.loads(v.guest('hyprctl activeworkspace -j'))['tiledLayout'] != before
    finally:
        if json.loads(v.guest('hyprctl activeworkspace -j'))['tiledLayout'] != before:
            v.guest('omarchy-hyprland-workspace-layout-toggle')
    before = v.guest('omarchy-shell notifications isDnd')
    try:
        v.guest('omarchy-toggle-notification-silencing')
        assert v.guest('omarchy-shell notifications isDnd') != before
    finally:
        if v.guest('omarchy-shell notifications isDnd') != before:
            v.guest('omarchy-toggle-notification-silencing')
    assert v.guest('hyprctl configerrors') in ('', 'ok')
    return 'Idle, nightlight, screensaver, bar, gaps and workspace layout changed and were restored.'


def package_picker_and_completion():
    for action in ('install', 'remove'):
        v.guest('setsid foot --app-id=omadora-picker-test python3 ~/source/tests/package-picker-probe.py ' + action + ' >/tmp/omadora-vm-results/picker.log 2>&1 </dev/null &')
        v.wait_for(lambda: any(c['class'] == 'omadora-picker-test' for c in json.loads(v.guest('hyprctl clients -j'))))
        v.wait_for(lambda: v.guest('pgrep -x fzf >/dev/null; echo $?') == '0', seconds=180)
        for char in 'ripgrep':
            v.keys(char)
        v.keys('tab')
        v.keys('ctrl', 'u')
        for char in 'fzf':
            v.keys(char)
        v.keys('tab')
        v.guest('grim /tmp/omadora-vm-results/picker-' + action + '.png')
        v.keys('ret')
        v.wait_for(lambda: v.guest('test -s /tmp/omadora-vm-results/picker-' + action + '.json; echo $?') == '0')
        selected = json.loads(v.guest('cat /tmp/omadora-vm-results/picker-' + action + '.json'))
        assert set(selected) == {'ripgrep', 'fzf'}, selected
        v.keys('ret')
        v.wait_for(lambda: not any(c['class'] == 'omadora-picker-test' for c in json.loads(v.guest('hyprctl clients -j'))))
    v.guest('setsid foot --app-id=omadora-completion-test omadora-terminal-action omarchy-webapp-install OmadoraCompletion https://example.com firefox >/tmp/omadora-vm-results/completion.log 2>&1 </dev/null &')
    v.wait_for(lambda: any(c['class'] == 'omadora-completion-test' for c in json.loads(v.guest('hyprctl clients -j'))))
    v.wait_for(lambda: v.guest('test -s ~/.local/share/applications/OmadoraCompletion.desktop; echo $?') == '0')
    v.guest('grim /tmp/omadora-vm-results/webapp-completion.png')
    v.keys('ret')
    v.wait_for(lambda: not any(c['class'] == 'omadora-completion-test' for c in json.loads(v.guest('hyprctl clients -j'))))
    v.guest('rm ~/.local/share/applications/OmadoraCompletion.desktop')
    return 'Real available/installed inventories filtered and multi-selected with keyboard; web-app completion closed with Enter.'


def screen_recording_and_reminder():
    def region():
        command = ('source ~/source/tests/vm-session.sh; '
                   'OMARCHY_SCREENRECORD_DIR=/tmp/omadora-vm-results/recordings '
                   'omarchy-capture-screenrecording >/tmp/omadora-vm-results/record-picker.log 2>&1')
        process = subprocess.Popen(v.ssh + ['bash -c ' + shlex.quote(command)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        v.wait_for(lambda: v.guest('pgrep -x slurp'))
        time.sleep(1)
        return process

    v.guest('omarchy-menu summon trigger.capture.screenrecord')
    time.sleep(2)
    v.guest('grim /tmp/omadora-vm-results/recording-menu.png')
    v.keys('esc')
    process = region()
    v.keys('esc')
    assert process.wait(30) == 0
    assert v.guest('omarchy-capture-screenrecording --status; echo $?') == '1'
    for mode in ('', '--with-desktop-audio', '--with-microphone-audio'):
        if mode:
            v.guest('OMARCHY_SCREENRECORD_DIR=/tmp/omadora-vm-results/recordings omarchy-capture-screenrecording --fullscreen ' + mode)
        else:
            process = region()
            v.keys('ctrl', 'ret')
            assert process.wait(30) == 0
        try:
            v.wait_for(lambda: v.guest('omarchy-capture-screenrecording --status; echo $?') == '0')
            # Move the pointer to ensure frames arrive even on a static desktop.
            for n in range(6):
                v.qmp('input-send-event', {'events': [{'type': 'rel', 'data': {'axis': 'x', 'value': 20}}]})
                time.sleep(.5)
            v.guest('grim /tmp/omadora-vm-results/recording-active.png')
        finally:
            v.guest('omarchy-capture-screenrecording --stop-recording', timeout=30)
            v.guest('cp "$XDG_RUNTIME_DIR/omadora-screenrecord/"*.log /tmp/omadora-vm-results/ || true')
        v.wait_for(lambda: v.guest('omarchy-capture-screenrecording --status; echo $?') == '1')
        latest = v.guest('find /tmp/omadora-vm-results/recordings -name "*.webm" | sort | tail -1')
        streams = json.loads(v.guest('ffprobe -v error -show_streams -of json ' + shlex.quote(latest)))['streams']
        assert any(s['codec_type'] == 'video' and s['width'] > 0 for s in streams), streams
        if mode:
            assert any(s['codec_type'] == 'audio' for s in streams), streams
        v.guest('ffmpeg -v error -i ' + shlex.quote(latest) + ' -frames:v 1 -f null -')
    v.guest('omarchy-reminder -i')
    time.sleep(2)
    v.guest('grim /tmp/omadora-vm-results/reminder-panel.png')
    v.keys('esc')
    v.guest('omarchy-reminder 1 Omadora-test')
    data = json.loads(v.guest('omarchy-reminder show --json'))
    assert data['count'] >= 1, data
    v.guest('omarchy-reminder clear')
    return 'Three saved and decoded WebM recordings: silent, desktop audio and microphone; reminder panel and timer creation/clear.'


v.check('desktop upgrade and rollback login', desktop_lifecycle)
v.check('package pickers and terminal completion', package_picker_and_completion)
v.check('screen recording and reminders', screen_recording_and_reminder)
v.check('menu dependencies and providers', menu_audit)
v.check('theme and bar controls', style_controls)
v.check('desktop toggles', desktop_toggles)
actions_spec = importlib.util.spec_from_file_location('desktop_actions', Path(__file__).with_name('desktop-actions.py'))
actions = importlib.util.module_from_spec(actions_spec)
actions_spec.loader.exec_module(actions)
actions.run_checks(v)
v.check('Activity shortcut', desktop_shortcuts)
v.check('screenshot keyboard and clipboard', screenshot_keyboard)
v.check('font preference preservation', font_preferences)
v.check('portal file chooser', portal)
v.check('network reconnect', network)
v.check('virtual audio controls', sound)
v.check('notifications', notifications)
v.check('GNOME and config recovery', recovery)
assert all(r['status'] == 'PASS' for r in v.results), v.results
