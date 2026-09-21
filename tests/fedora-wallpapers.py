"""Real pywal16 and installed theme templates in the disposable Fedora container."""
import json
from pathlib import Path
import sys
import tempfile
import tomllib

ROOT = Path('/usr/local/share/omadora')
sys.path.insert(0, str(ROOT))
from omadora_wallpapers import Library, DEFAULT
from PIL import Image

lib = Library(root=ROOT)
current = Path.home() / '.local/state/omarchy/current'
assert (current / 'theme.name').read_text().strip() == 'omadora-wallpaper'
assert (current / 'background').resolve().name == DEFAULT
initial = tomllib.loads((current / 'theme/colors.toml').read_text())
for name in ('shell.toml', 'foot.ini', 'hyprland.lua', 'neovim.lua', 'gum_env.lua'):
    text = (current / 'theme' / name).read_text()
    assert '{{' not in text, name
    assert len(text) > 40, name

with tempfile.TemporaryDirectory() as tmp:
    image = Image.new('RGB', (128, 128))
    for x in range(128):
        for y in range(128): image.putpixel((x, y), (min(255, x * 2), y, (x + y) // 3))
    source = Path(tmp) / 'test wallpaper.png'; image.save(source)
    row = lib.add(source)
    lib.apply(row['id'], headless=True)
    changed = tomllib.loads((current / 'theme/colors.toml').read_text())
    assert changed != initial, 'Selecting another image must generate another palette'
    assert lib.load()['selected'] == row['id']
    assert changed['accent'] in (current / 'theme/hyprland.lua').read_text()
    assert changed['accent'].lstrip('#') in (current / 'theme/foot.ini').read_text()
    assert changed['accent'] in (Path.home() / '.config/gtk-4.0/omadora-colors.css').read_text()
    # Removal applies the default first and keeps the original user file.
    import os
    os.environ['OMARCHY_THEME_HEADLESS'] = '1'
    lib.remove(row['id'])
    assert source.exists()
    assert (current / 'background').resolve().name == DEFAULT
    assert tomllib.loads((current / 'theme/colors.toml').read_text()) == initial

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
provider = Gtk.CssProvider()
errors = []
provider.connect('parsing-error', lambda _p, _s, error: errors.append(str(error)))
provider.load_from_path(str(Path.home() / '.config/gtk-4.0/gtk.css'))
assert not errors, errors
print('PASS: default Nepal, real pywal palette extraction, theme templates, GTK CSS, add/apply/remove, original-file preservation')
