"""Real keyboard and rendering checks, driven through the VM's QMP seat."""
import json
import shlex
import time


def run_checks(v):
    def active():
        return json.loads(v.guest('hyprctl activewindow -j'))

    def clients():
        return json.loads(v.guest('hyprctl clients -j'))

    def copy(text):
        # Redirect inside the guest; the clipboard owner retains descriptors.
        v.guest('printf %s ' + shlex.quote(text) + ' | wl-copy >/dev/null 2>&1')

    def launch(command):
        v.guest('nohup ' + command + ' >/tmp/omadora-vm-results/action-launch.log 2>&1 </dev/null &')

    def window_shortcuts():
        v.keys('meta_l', '1')
        before = {c['address'] for c in clients()}
        try:
            v.keys('meta_l', 'ret')
            v.wait_for(lambda: active().get('class') == 'foot' and active()['address'] not in before)
            first = active()['address']
            v.keys('meta_l', 'ret')
            v.wait_for(lambda: active().get('class') == 'foot' and active()['address'] != first)
            second = active()['address']
            v.keys('meta_l', 'f')
            v.wait_for(lambda: bool(active().get('fullscreen')))
            v.keys('meta_l', 'f')
            v.wait_for(lambda: not active().get('fullscreen'))
            v.keys('meta_l', 't')
            v.wait_for(lambda: active().get('floating'))
            v.keys('meta_l', 't')
            v.wait_for(lambda: not active().get('floating'))
            v.keys('meta_l', 'shift', '2')
            v.wait_for(lambda: any(c['address'] == second and c['workspace']['id'] == 2 for c in clients()))
            v.keys('meta_l', '2')
            v.wait_for(lambda: active().get('address') == second)
            v.guest('grim /tmp/omadora-vm-results/window-workspace.png')
            v.keys('meta_l', 'w')
            v.wait_for(lambda: not any(c['address'] == second for c in clients()))
            v.keys('meta_l', '1')
            v.wait_for(lambda: active().get('address') == first)
            v.keys('meta_l', 'w')
            v.wait_for(lambda: not any(c['address'] == first for c in clients()))
            return 'Two real terminals; fullscreen and floating round trips; move to workspace 2, follow, close and return to workspace 1.'
        finally:
            # Restrict cleanup to windows created by this test.
            for client in clients():
                if client['address'] not in before:
                    expression = 'hl.dsp.window.close({window=' + json.dumps('address:' + client['address']) + '})'
                    v.guest('hyprctl dispatch ' + shlex.quote(expression))
            v.keys('meta_l', '1')

    def universal_clipboard():
        launch('python3 ~/source/tests/clipboard-entry.py')
        v.wait_for(lambda: active().get('title') == 'Omadora clipboard fixture')
        try:
            v.keys('ctrl', 'a')
            v.keys('meta_l', 'c')
            v.wait_for(lambda: v.guest('wl-paste --no-newline') == 'Omadora copy from GTK')
            v.keys('meta_l', 'x')
            v.wait_for(lambda: v.guest('cat /tmp/omadora-entry.txt') == '')
            assert v.guest('wl-paste --no-newline') == 'Omadora copy from GTK'
            copy('Omadora paste into GTK')
            v.keys('meta_l', 'v')
            v.wait_for(lambda: v.guest('cat /tmp/omadora-entry.txt') == 'Omadora paste into GTK')
            v.guest('grim /tmp/omadora-vm-results/clipboard-gtk.png')
        finally:
            v.guest('pkill -f "^python3 /home/omadora-test/source/tests/clipboard-entry.py$" || true')
        # The normal Foot class is essential: the desktop routes paste through
        # its terminal tag, using Shift+Insert instead of Ctrl+V.
        script = 'IFS= read -r line; printf "%s" "$line" > /tmp/omadora-terminal-paste.txt; sleep 60'
        launch('foot --title=Omadora-terminal-paste bash -c ' + shlex.quote(script))
        v.wait_for(lambda: active().get('title') == 'Omadora-terminal-paste')
        try:
            assert any(t.rstrip('*') == 'terminal' for t in active().get('tags', [])), active()
            copy('Omadora paste into terminal')
            v.keys('meta_l', 'v')
            v.keys('ret')
            v.wait_for(lambda: v.guest('cat /tmp/omadora-terminal-paste.txt') == 'Omadora paste into terminal')
        finally:
            v.keys('meta_l', 'w')
        return 'Super+C/X/V copied, cut and pasted in GTK; Super+V pasted exact text into a terminal through the terminal-specific binding.'

    def display_scaling():
        original = float(v.guest('omarchy-hyprland-monitor-scaling'))
        try:
            v.keys('meta_l', 'slash')
            v.wait_for(lambda: float(v.guest('omarchy-hyprland-monitor-scaling')) > original)
            assert v.guest('hyprctl configerrors') in ('', 'ok')
            v.guest('omarchy-shell shell summon omarchy.monitor')
            time.sleep(1)
            v.guest('grim /tmp/omadora-vm-results/display-scaled.png')
            v.guest('omarchy-shell shell hide omarchy.monitor')
            v.keys('meta_l', 'alt', 'slash')
            v.wait_for(lambda: abs(float(v.guest('omarchy-hyprland-monitor-scaling')) - original) < .001)
        finally:
            v.guest('omarchy-hyprland-monitor-scaling ' + str(original))
        assert v.guest('omarchy-shell shell ping') == 'ok'
        return 'Display scaling increased through Super+/ and returned through Super+Alt+/; compositor configuration stayed valid.'

    v.check('window shortcut transitions', window_shortcuts)
    v.check('universal clipboard in GTK and Foot', universal_clipboard)
    v.check('display scaling shortcuts', display_scaling)
