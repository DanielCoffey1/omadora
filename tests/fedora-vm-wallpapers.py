"""Wallpaper browser and live shell palette acceptance in the disposable VM."""
import importlib.util
import json
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('interactions', Path(__file__).with_name('fedora-vm-interactions.py'))
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)


def browser():
    clients = json.loads(v.guest('hyprctl clients -j'))
    return next((c for c in clients if c['class'] == 'org.omadora.Wallpapers'), None)


def click(x, y):
    v.qmp('input-send-event', {'events': [
        {'type': 'abs', 'data': {'axis': 'x', 'value': round(x * 32767 / 1920)}},
        {'type': 'abs', 'data': {'axis': 'y', 'value': round(y * 32767 / 1080)}},
        {'type': 'btn', 'data': {'button': 'left', 'down': True}},
        {'type': 'btn', 'data': {'button': 'left', 'down': False}}]})
    time.sleep(.5)


def test():
    assert v.guest('cat ~/.local/state/omarchy/current/theme.name') == 'omadora-wallpaper'
    assert v.guest('readlink -f ~/.local/state/omarchy/current/background').endswith('Nepal_5160x2160.png')
    before = v.guest('cat ~/.local/state/omarchy/current/theme/colors.toml')
    # Use the actual Style menu action, as configured for users.
    v.guest('nohup omadora wallpaper browse >/tmp/omadora-vm-results/wallpaper-browser.log 2>&1 </dev/null &')
    v.wait_for(browser, 30)
    window = browser(); x, y = window['at']
    time.sleep(3)
    v.guest('grim /tmp/omadora-vm-results/wallpaper-browser.png')
    # A real click on the first preview applies it asynchronously.
    click(x + 150, y + 185)
    first = json.loads(v.guest('omadora wallpaper list'))[0]
    def selected():
        return json.loads(v.guest('cat ~/.local/share/omadora/wallpapers/library.json'))['selected'] == first['id']
    v.wait_for(selected, 100)
    after = v.guest('cat ~/.local/state/omarchy/current/theme/colors.toml')
    assert before != after
    v.guest('grim /tmp/omadora-vm-results/wallpaper-applied.png')
    # Confirm the compositor still accepts commands and the themed shell is alive.
    assert json.loads(v.guest('hyprctl monitors -j'))
    assert v.guest('omarchy-shell -q shell isReady') == 'true'
    v.guest('omadora wallpaper apply Nepal_5160x2160.png', timeout=150)
    v.guest('grim /tmp/omadora-vm-results/wallpaper-nepal.png')
    return 'Nepal initialized; GTK wallpaper browser rendered; clicking a downloaded wallpaper regenerated colors; Nepal restored; compositor and shell remained responsive.'


v.check('wallpaper browser and live palette', test)
assert all(r['status'] == 'PASS' for r in v.results), v.results
