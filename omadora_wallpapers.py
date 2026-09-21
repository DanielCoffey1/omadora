"""Wallpaper library and pywal16 palettes, applied through the desktop templates."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
THEME = 'omadora-wallpaper'
DEFAULT = 'Nepal_5160x2160.png'


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(text)
    os.replace(f.name, path)


def mix(a, b, amount):
    return '#' + ''.join(f'{round(int(a[i:i+2],16)*(1-amount)+int(b[i:i+2],16)*amount):02x}' for i in (1, 3, 5))


def palette(data):
    c = data['colors']; bg = data['special']['background']; fg = data['special']['foreground']
    for color in [bg, fg, *[c[f'color{i}'] for i in range(16)]]:
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', str(color)):
            raise ValueError('pywal returned an invalid color.')
    # Retain a readable dark surface while using the image's accent and ANSI palette.
    bg = mix(bg, '#000000', .25)
    fg = mix(fg, '#ffffff', .25)
    result = dict(mode='dark', accent=c['color4'], selection=mix(bg, c['color4'], .35),
                  muted=mix(bg, fg, .35), background=bg, dark_background=mix(bg, '#000000', .2),
                  darker_background=mix(bg, '#000000', .4), lighter_background=mix(bg, fg, .1),
                  foreground=fg, dark_foreground=mix(bg, fg, .6), light_foreground=mix(fg, '#ffffff', .2),
                  bright_foreground=mix(fg, '#ffffff', .4), orange=mix(c['color1'], c['color3'], .5),
                  brown=mix(c['color3'], bg, .5))
    for name, index in dict(red=1, green=2, yellow=3, blue=4, magenta=5, cyan=6).items():
        result[name] = c[f'color{index}']; result['bright_'+name] = c[f'color{index+8}']
    return result


class Library:
    def __init__(self, home=None, root=None):
        self.home = Path(home or Path.home())
        self.root = Path(root or ROOT)
        self.assets = self.root / 'assets/wallpapers'
        self.catalog = json.loads((self.assets / 'catalog.json').read_text())
        self.directory = self.home / '.local/share/omadora/wallpapers'
        self.state = self.directory / 'library.json'
        self.cache = self.home / '.cache/omadora/wallpapers'
        for relative in ('.local/share/omadora/wallpapers', '.cache/omadora/wallpapers',
                         '.config/omarchy/themes', '.local/state/omarchy/current',
                         '.config/gtk-3.0', '.config/gtk-4.0', '.config/qt6ct/colors'):
            for part in [Path(relative), *Path(relative).parents]:
                if (self.home / part).is_symlink():
                    raise ValueError('Wallpaper storage/config parent must not be a symlink: ' + str(part))


    def load(self):
        return json.loads(self.state.read_text()) if self.state.exists() else dict(hidden=[], added=[], selected=None)

    def save(self, state):
        atomic(self.state, json.dumps(state, indent=2))

    @contextlib.contextmanager
    def locked(self):
        import fcntl
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / '.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def entries(self):
        state = self.load()
        return [r for r in self.catalog['images'] + state['added'] if r['id'] not in state['hidden']]

    def lookup(self, value):
        matches = [r for r in self.entries() if value in (r['id'], r['name'])]
        if len(matches) != 1:
            raise ValueError('Wallpaper not found or name is ambiguous; select it from the browser.')
        return matches[0]

    def file(self, row):
        if row.get('local'):
            path = self.directory / row['local']
        elif row['name'] == DEFAULT:
            path = self.assets / DEFAULT
        elif (self.assets / 'originals' / row['id']).is_file():
            path = self.assets / 'originals' / row['id']
        else:
            self.cache.mkdir(parents=True, exist_ok=True)
            path = self.cache / row['id']
            if not path.exists():
                # Download into a temporary file; interrupted downloads never become cached images.
                with tempfile.NamedTemporaryFile(dir=self.cache, delete=False) as temp:
                    temporary = Path(temp.name)
                    try:
                        with urlopen(self.catalog['base_url'] + quote(row['asset']), timeout=45) as response:
                            total = 0
                            while chunk := response.read(1024 * 1024):
                                total += len(chunk)
                                if total > row['size']:
                                    raise ValueError('Wallpaper download exceeds the catalog size.')
                                temp.write(chunk)
                        temp.close()
                        if hashlib.sha256(temporary.read_bytes()).hexdigest() != row['sha256']:
                            raise ValueError('Wallpaper checksum failed; previous theme kept.')
                        os.replace(temporary, path)
                    finally:
                        temporary.unlink(missing_ok=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Wallpaper file changed or is damaged.')
        return path

    def preview(self, row):
        return self.directory / (row['id'] + '.jpg') if row.get('local') else self.assets / 'previews' / (row['id'] + '.jpg')

    def add(self, source):
        from PIL import Image, ImageOps
        source = Path(source).expanduser().resolve(strict=True)
        if source.stat().st_size > 100 * 1024 * 1024:
            raise ValueError('Please choose an image smaller than 100 MB.')
        content = source.read_bytes(); digest = hashlib.sha256(content).hexdigest()
        with self.locked():
            state = self.load()
            existing = next((r for r in self.catalog['images'] + state['added'] if r['id'] == digest), None)
            if existing:
                state['hidden'] = [v for v in state['hidden'] if v != digest]
                self.save(state)
                return existing
            with Image.open(source) as im:
                if im.format not in ('PNG', 'JPEG', 'WEBP', 'GIF', 'BMP'):
                    raise ValueError('Choose a PNG, JPEG, WebP, GIF or BMP image.')
                im.seek(0)
                preview = ImageOps.fit(im.convert('RGB'), (320, 180))
            local = digest + source.suffix.lower()
            (self.directory / local).write_bytes(content)
            preview.save(self.directory / (digest + '.jpg'), quality=80)
            row = dict(id=digest, sha256=digest, name=source.name, size=len(content), local=local)
            state['hidden'] = [v for v in state['hidden'] if v != digest]
            state['added'].append(row); self.save(state)
            return row

    def generate(self, image):
        self.cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.cache) as temp:
            temp = Path(temp)
            # Normalize input and bound the extraction cost, including animated/large images.
            from PIL import Image, ImageOps
            with Image.open(image) as im:
                im.seek(0)
                normalized = ImageOps.exif_transpose(im).convert('RGB')
                normalized.thumbnail((1024, 1024))
                normalized.save(temp / 'palette.png')
            env = dict(os.environ, PYTHONPATH=str(self.root / 'vendor'))
            script = 'import json,sys; from pywal.colors import get; print(json.dumps(get(sys.argv[1],cache_dir=sys.argv[2],c16="darken")))'
            result = subprocess.run([sys.executable, '-c', script, str(temp / 'palette.png'), str(temp)],
                                    env=env, text=True, capture_output=True, timeout=120)
            if result.returncode:
                raise ValueError('pywal could not generate colors: ' + result.stderr[-1500:])
            return palette(json.loads(result.stdout))

    def apply(self, value, headless=False):
        with self.locked():
            row = self.lookup(value)
            self._apply(row, headless)

    def _apply(self, row, headless=False):
        image = self.file(row)
        colors = self.generate(image)
        with self.theme_transaction():
            self.commit_theme(row, image, colors, headless)

    def commit_theme(self, row, image, colors, headless):
        themes = self.home / '.config/omarchy/themes'
        themes.mkdir(parents=True, exist_ok=True)
        target = themes / THEME
        if target.exists() and not (target / '.omadora-generated').exists():
            raise ValueError('The generated theme location contains a user theme; rename it before continuing.')
        with tempfile.TemporaryDirectory(dir=themes) as temporary:
            stage = Path(temporary) / THEME; stage.mkdir()
            (stage / '.omadora-generated').touch()
            (stage / 'colors.toml').write_text(''.join(f'{k} = "{v}"\n' for k, v in colors.items()))
            (stage / 'backgrounds').mkdir()
            shutil.copy2(image, stage / 'backgrounds' / row['name'])
            old = Path(temporary) / 'previous'
            if target.exists():
                target.rename(old)
            stage.rename(target)
            env = dict(os.environ, HOME=str(self.home), OMARCHY_PATH=str(self.root / 'upstream'),
                       PATH=str(self.root / 'bin') + ':' + str(self.root / 'upstream/bin') + ':' + os.environ.get('PATH', ''))
            if headless:
                env['OMARCHY_THEME_HEADLESS'] = '1'
            try:
                subprocess.run([self.root / 'upstream/bin/omarchy-theme-set', THEME], env=env, check=True, timeout=120)
            except BaseException:
                shutil.rmtree(target)
                if old.exists():
                    old.rename(target)
                raise
        self.toolkit_colors(colors)
        state = self.load(); state['selected'] = row['id']; self.save(state)

    @contextlib.contextmanager
    def theme_transaction(self):
        # Save the last working generated state before the upstream apply script
        # swaps its theme directory. Restore it if a hook or toolkit write fails.
        paths = ['.local/state/omarchy/current', '.config/omarchy/themes/' + THEME,
                 '.local/share/omadora/wallpapers/library.json',
                 '.config/gtk-3.0/gtk.css', '.config/gtk-3.0/omadora-colors.css',
                 '.config/gtk-4.0/gtk.css', '.config/gtk-4.0/omadora-colors.css',
                 '.config/qt6ct/qt6ct.conf', '.config/qt6ct/colors/Omadora.conf']
        self.cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.cache) as temporary:
            saved = []
            for index, relative in enumerate(paths):
                path = self.home / relative
                backup = Path(temporary) / str(index)
                exists = path.exists() or path.is_symlink()
                if exists:
                    if path.is_symlink(): backup.symlink_to(os.readlink(path))
                    elif path.is_dir(): shutil.copytree(path, backup, symlinks=True)
                    else: shutil.copy2(path, backup)
                saved.append((path, backup, exists))
            try:
                yield
            except BaseException:
                for path, backup, existed in reversed(saved):
                    if path.is_symlink() or path.is_file(): path.unlink()
                    elif path.is_dir(): shutil.rmtree(path)
                    if existed:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        if backup.is_symlink(): path.symlink_to(os.readlink(backup))
                        elif backup.is_dir(): shutil.copytree(backup, path, symlinks=True)
                        else: shutil.copy2(backup, path)
                raise

    def toolkit_colors(self, c):
        definitions = dict(theme_bg_color=c['background'], theme_fg_color=c['foreground'],
                           theme_base_color=c['dark_background'], theme_text_color=c['foreground'],
                           theme_selected_bg_color=c['accent'], theme_selected_fg_color=c['background'],
                           accent_bg_color=c['accent'], accent_fg_color=c['background'], accent_color=c['accent'],
                           window_bg_color=c['background'], window_fg_color=c['foreground'],
                           view_bg_color=c['dark_background'], view_fg_color=c['foreground'],
                           headerbar_bg_color=c['lighter_background'], headerbar_fg_color=c['foreground'],
                           card_bg_color=c['lighter_background'], card_fg_color=c['foreground'],
                           popover_bg_color=c['lighter_background'], popover_fg_color=c['foreground'],
                           dialog_bg_color=c['background'], dialog_fg_color=c['foreground'])
        css = ''.join(f'@define-color {k} {v};\n' for k, v in definitions.items())
        css += '.background { background-color: @theme_bg_color; color: @theme_fg_color; }\n'
        for version in ('3.0', '4.0'):
            directory = self.home / '.config' / ('gtk-' + version)
            extra = '' if version == '3.0' else ':root {\n' + ''.join(f'  --{k.replace("_", "-")}: {v};\n' for k, v in definitions.items() if not k.startswith('theme_')) + '}\n'
            atomic(directory / 'omadora-colors.css', css + extra)
            main = directory / 'gtk.css'
            previous = main.read_text() if main.exists() else ''
            line = '@import url("omadora-colors.css");'
            if line not in previous:
                atomic(main, line + '\n' + previous)
        # Qt6ct uses the standard QPalette role order (active/inactive/disabled).
        roles = [c['foreground'], c['lighter_background'], c['bright_foreground'], c['muted'],
                 c['dark_background'], c['muted'], c['foreground'], '#ffffff', c['foreground'],
                 c['background'], c['background'], '#000000', c['accent'], c['background'],
                 c['blue'], c['magenta'], c['lighter_background'], c['dark_background'],
                 c['foreground'], c['background'], c['foreground']]
        atomic(self.home / '.config/qt6ct/colors/Omadora.conf', '[ColorScheme]\n' + ''.join(f'{group}_colors=' + ', '.join(roles) + '\n' for group in ('active', 'inactive', 'disabled')))
        import configparser
        path = self.home / '.config/qt6ct/qt6ct.conf'
        conf = configparser.ConfigParser()
        if path.exists(): conf.read(path)
        if not conf.has_section('Appearance'): conf.add_section('Appearance')
        conf['Appearance'].update(style='Fusion', custom_palette='true', color_scheme_path=str(self.home / '.config/qt6ct/colors/Omadora.conf'))
        import io
        output = io.StringIO(); conf.write(output); atomic(path, output.getvalue())

    def remove(self, value):
        with self.locked():
            row = self.lookup(value)
            others = [r for r in self.entries() if r['id'] != row['id']]
            if not others:
                raise ValueError('Keep at least one wallpaper in the library.')
            state = self.load()
            if state.get('selected') == row['id']:
                replacement = next((r for r in others if r['name'] == DEFAULT), others[0])
                self._apply(replacement)
                state = self.load()
            state['hidden'].append(row['id'])
            if row.get('local'):
                state['added'] = [r for r in state['added'] if r['id'] != row['id']]
                (self.directory / row['local']).unlink(missing_ok=True)
                self.preview(row).unlink(missing_ok=True)
            else:
                (self.cache / row['id']).unlink(missing_ok=True)
            self.save(state)


def main(action, value=None, headless=False):
    lib = Library()
    if action in ('browse', 'add-dialog', 'remove-dialog'):
        from omadora_wallpaper_browser import run
        return run(lib, action)
    if action == 'list':
        print(json.dumps(lib.entries(), indent=2))
    elif action == 'apply':
        lib.apply(value or DEFAULT, headless)
    elif action == 'add':
        print(lib.add(value)['name'])
    elif action == 'remove':
        lib.remove(value)
    elif action == 'next':
        rows = lib.entries(); current = lib.load().get('selected')
        index = next((i for i, r in enumerate(rows) if r['id'] == current), -1)
        lib.apply(rows[(index + 1) % len(rows)]['id'], headless)
