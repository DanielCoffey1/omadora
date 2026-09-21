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
    # The wallpaper VM has a USB tablet for direct absolute pointer input.
    v.qmp('input-send-event', {'events': [
        {'type': 'abs', 'data': {'axis': 'x', 'value': round(x * 32767 / 1920)}},
        {'type': 'abs', 'data': {'axis': 'y', 'value': round(y * 32767 / 1080)}}]})
    time.sleep(.3)
    for down in (True, False):
        v.qmp('input-send-event', {'events': [{'type': 'btn', 'data': {'button': 'left', 'down': down}}]})
        time.sleep(.15)
    time.sleep(.5)


def test():
    assert v.guest('cat ~/.local/state/omarchy/current/theme.name') == 'omadora-wallpaper'
    assert v.guest('readlink -f ~/.local/state/omarchy/current/background').endswith('Nepal_5160x2160.png')
    before = v.guest('cat ~/.local/state/omarchy/current/theme/colors.toml')
    # Verify and execute the Style menu action configured for users.
    menu = json.loads(v.guest('cat $OMARCHY_PATH/default/omarchy/omarchy-menu.jsonc'))
    assert menu['style.wallpapers']['action'] == 'omadora wallpaper browse'
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
    try:
        v.wait_for(selected, 100)
    finally:
        v.guest('grim /tmp/omadora-vm-results/wallpaper-after-click.png')
        v.guest('cp ~/.local/share/omadora/wallpapers/library.json /tmp/omadora-vm-results/wallpaper-state.json')
    after = v.guest('cat ~/.local/state/omarchy/current/theme/colors.toml')
    assert before != after
    v.guest('grim /tmp/omadora-vm-results/wallpaper-applied.png')
    # Confirm the compositor still accepts commands and the themed shell is alive.
    assert json.loads(v.guest('hyprctl monitors -j'))
    assert v.guest('omarchy-shell shell ping') == 'ok'
    # Native Add dialog: import a user image with real keyboard input.
    v.guest("python3 -c \"from PIL import Image; Image.new('RGB',(80,60),'#52697b').save('/tmp/omadora-test.png')\"")
    window = browser(); x, y = window['at']; width = window['size'][0]
    click(x + width - 240, y + 35)
    v.wait_for(lambda: any(c['title'] == 'Add wallpapers' for c in json.loads(v.guest('hyprctl clients -j'))), 20)
    v.guest('grim /tmp/omadora-vm-results/wallpaper-add-dialog.png')
    v.keys('ctrl', 'l')
    for char in '/tmp/omadora-test.png':
        v.keys({'/': 'slash', '-': 'minus', '.': 'dot'}.get(char, char))
    v.keys('ret')
    v.wait_for(lambda: any(r['name'] == 'omadora-test.png' for r in json.loads(v.guest('omadora wallpaper list'))), 25)
    # Remove the active wallpaper through its confirmation dialog.
    click(x + width - 90, y + 35)
    def dialog():
        return next((c for c in json.loads(v.guest('hyprctl clients -j')) if c['class'] == 'org.omadora.Wallpapers' and c['address'] != window['address']), None)
    v.wait_for(dialog, 15)
    prompt = dialog()
    v.guest('grim /tmp/omadora-vm-results/wallpaper-remove-dialog.png')
    click(prompt['at'][0] + prompt['size'][0] - 45, prompt['at'][1] + prompt['size'][1] - 25)
    v.wait_for(lambda: first['id'] not in [r['id'] for r in json.loads(v.guest('omadora wallpaper list'))], 100)
    assert v.guest('test -f /tmp/omadora-test.png && echo kept') == 'kept'
    assert v.guest('readlink -f ~/.local/state/omarchy/current/background').endswith('Nepal_5160x2160.png')
    v.guest('grim /tmp/omadora-vm-results/wallpaper-nepal.png')
    return 'Nepal initialized; GTK wallpaper browser rendered; clicking a downloaded wallpaper regenerated colors; Add dialog imported an image; Remove dialog removed the active wallpaper and restored Nepal; compositor and shell remained responsive.'


v.check('wallpaper browser and live palette', test)
assert all(r['status'] == 'PASS' for r in v.results), v.results
