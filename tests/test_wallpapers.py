import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import omadora_wallpapers as wall


class Wallpapers(unittest.TestCase):
    def test_collection_default_and_previews_are_complete(self):
        lib = wall.Library()
        self.assertEqual(len(lib.catalog['images']), 332)
        self.assertEqual(len({r['id'] for r in lib.catalog['images']}), 332)
        for row in lib.catalog['images']:
            self.assertTrue(lib.preview(row).is_file())
            self.assertRegex(row['asset'], r'^[0-9a-f]{64}\.[a-z]+$')
        row = lib.lookup(wall.DEFAULT)
        self.assertEqual(hashlib.sha256(lib.file(row).read_bytes()).hexdigest(), row['id'])

    def test_download_failure_keeps_selection_and_does_not_cache_bad_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = wall.Library(tmp)
            lib.save(dict(hidden=[], added=[], selected='previous'))
            row = next(r for r in lib.entries() if r['name'] != wall.DEFAULT)
            with patch.object(wall, 'urlopen', return_value=io.BytesIO(b'wrong image')):
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    lib.file(row)
            self.assertEqual(lib.load()['selected'], 'previous')
            self.assertFalse((lib.cache / row['id']).exists())
            self.assertEqual(list(lib.cache.iterdir()), [])

    def test_add_remove_keeps_original_and_readding_unhides_builtin(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(wall.Library, 'locked', contextlib.nullcontext):
            lib = wall.Library(tmp)
            row = lib.lookup(wall.DEFAULT)
            lib.remove(row['id'])
            self.assertNotIn(row['id'], [r['id'] for r in lib.entries()])
            lib.add(lib.assets / wall.DEFAULT)
            self.assertEqual(lib.lookup(wall.DEFAULT)['id'], row['id'])
            from PIL import Image
            original = Path(tmp) / 'original image.png'
            Image.new('RGB', (80, 60), '#52697b').save(original)
            row = lib.add(original)
            self.assertTrue(lib.file(row).exists())
            lib.remove(row['id'])
            self.assertTrue(original.exists())
            self.assertFalse((lib.directory / row['local']).exists())

    def test_failed_replacement_does_not_remove_active_wallpaper(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(wall.Library, 'locked', contextlib.nullcontext):
            lib = wall.Library(tmp)
            row = lib.lookup(wall.DEFAULT)
            lib.save(dict(hidden=[], added=[], selected=row['id']))
            with patch.object(lib, '_apply', side_effect=ValueError('unavailable')):
                with self.assertRaises(ValueError): lib.remove(row['id'])
            self.assertEqual(lib.lookup(wall.DEFAULT), row)
            self.assertEqual(lib.load()['selected'], row['id'])

    def test_palette_rejects_code_and_toolkit_files_preserve_user_css(self):
        data = dict(colors={f'color{i}': '#667788' for i in range(16)},
                    special=dict(background='#112233', foreground='#ddeeff'))
        colors = wall.palette(data)
        with tempfile.TemporaryDirectory() as tmp:
            lib = wall.Library(tmp)
            css = Path(tmp) / '.config/gtk-4.0/gtk.css'
            css.parent.mkdir(parents=True)
            css.write_text('/* user settings */\n')
            lib.toolkit_colors(colors); lib.toolkit_colors(colors)
            self.assertEqual(css.read_text().count('@import'), 1)
            self.assertIn('/* user settings */', css.read_text())
            self.assertIn(colors['accent'], (css.parent / 'omadora-colors.css').read_text())
            self.assertIn('custom_palette = true', (Path(tmp) / '.config/qt6ct/qt6ct.conf').read_text())
        data['colors']['color3'] = '"; os.execute("bad")'
        with self.assertRaises(ValueError): wall.palette(data)

    def test_generated_theme_failure_restores_previous_source(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(wall.Library, 'locked', contextlib.nullcontext):
            lib = wall.Library(tmp)
            target = Path(tmp) / '.config/omarchy/themes' / wall.THEME
            target.mkdir(parents=True); (target / '.omadora-generated').touch()
            (target / 'colors.toml').write_text('old palette')
            with patch.object(lib, 'generate', return_value=dict(background='#112233')), patch.object(wall.subprocess, 'run', side_effect=RuntimeError('template failure')):
                with self.assertRaises(RuntimeError): lib.apply(wall.DEFAULT)
            self.assertEqual((target / 'colors.toml').read_text(), 'old palette')
            self.assertIsNone(lib.load()['selected'])

    def test_late_toolkit_failure_restores_current_palette_and_selection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(wall.Library, 'locked', contextlib.nullcontext):
            lib = wall.Library(tmp)
            current = Path(tmp) / '.local/state/omarchy/current'
            current.mkdir(parents=True)
            (current / 'theme.name').write_text('previous-theme')
            lib.save(dict(hidden=[], added=[], selected='previous-wallpaper'))
            def applied(*args, **kwargs):
                (current / 'theme.name').write_text('omadora-wallpaper')
            with patch.object(lib, 'generate', return_value=dict(background='#112233')), patch.object(wall.subprocess, 'run', side_effect=applied), patch.object(lib, 'toolkit_colors', side_effect=OSError('disk error')):
                with self.assertRaises(OSError): lib.apply(wall.DEFAULT)
            self.assertEqual((current / 'theme.name').read_text(), 'previous-theme')
            self.assertEqual(lib.load()['selected'], 'previous-wallpaper')
