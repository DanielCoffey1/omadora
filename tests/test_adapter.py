import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('omadora', ROOT / 'omadora.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class AdapterTests(unittest.TestCase):
    def test_only_supported_fedora(self):
        good = {'ID': 'fedora', 'VARIANT_ID': 'workstation', 'VERSION_ID': '44'}
        adapter.validate_target(good, 'x86_64')
        for changes, arch, atomic in [({'ID': 'arch'}, 'x86_64', False),
                                     ({'VERSION_ID': '43'}, 'x86_64', False),
                                     ({'VARIANT_ID': 'silverblue'}, 'x86_64', True),
                                     ({}, 'aarch64', False), ({}, 'x86_64', True)]:
            with self.assertRaises(ValueError):
                adapter.validate_target(good | changes, arch, atomic)

    def test_steam_is_native_and_repos_are_only_optional(self):
        apps = adapter.read_json(ROOT / 'apps.json')
        commands = adapter.app_commands(apps['steam'], 'install')
        self.assertEqual(commands[-1], ['sudo', 'dnf', 'install', 'steam'])
        self.assertIn('rpmfusion-free-release-44', commands[0][-1])
        self.assertEqual(adapter.app_commands(apps['steam'], 'remove'), [['sudo', 'dnf', 'remove', 'steam']])
        self.assertNotIn('steam', adapter.packages())
        self.assertNotIn('libreoffice', adapter.packages())
        self.assertNotIn('podman', adapter.packages())

    def test_flatpak_has_explicit_user_scope_and_id(self):
        app = adapter.read_json(ROOT / 'apps.json')['heroic']
        commands = adapter.app_commands(app, 'install')
        self.assertEqual(commands[-1], ['flatpak', 'install', '--user', 'flathub', 'com.heroicgameslauncher.hgl'])
        self.assertEqual(adapter.app_commands(app, 'remove'), [['flatpak', 'uninstall', '--user', 'com.heroicgameslauncher.hgl']])

    def test_steam_launcher_actions_and_custom_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            desktop = home / 'system-steam.desktop'
            adapter.write(desktop, '[Desktop Entry]\nExec=/usr/bin/steam %U\n[Desktop Action Store]\nExec=/usr/bin/steam steam://store\n')
            target = home / '.local/share/applications/steam.desktop'
            adapter.steam_launcher('install', home, desktop)
            self.assertEqual(target.read_text().count('Exec=/usr/local/share/omadora/bin/steam'), 2)
            adapter.steam_launcher('check', home, desktop)
            adapter.steam_launcher('remove', home, desktop)
            self.assertFalse(target.exists())
            adapter.steam_launcher('install', home, desktop)
            adapter.write(target, 'user customization')
            with self.assertRaisesRegex(ValueError, 'Preserving custom'):
                adapter.steam_launcher('check', home, desktop)
            adapter.steam_launcher('remove', home, desktop)
            self.assertEqual(target.read_text(), 'user customization')

    def test_catalog_cannot_inject_flags_or_shell(self):
        import re
        for app_id, app in adapter.read_json(ROOT / 'apps.json').items():
            self.assertRegex(app_id, r'^[a-z0-9-]+$')
            self.assertIn(app['source'], ('dnf', 'flatpak', 'rpmfusion'))
            for p in app.get('packages', [app.get('id')]):
                self.assertTrue(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', p))

    def test_menu_replaces_arch_actions_and_keeps_hierarchy(self):
        original = {'install': {'label': 'Install'}, 'install.gaming': {'label': 'Gaming'},
                    'install.gaming.steam': {'action': 'yay -S steam'},
                    'system.lock': {'action': 'omarchy-system-lock'},
                    'setup.bad': {'action': 'omarchy-setup-disk'},
                    'style': {'label': 'Style'}, 'style.theme': {'action': 'omarchy-theme-switcher'}}
        menu = adapter.menu_for_fedora(original, adapter.read_json(ROOT / 'apps.json'), ['omarchy-setup-disk'])
        self.assertEqual(menu['system.lock'], original['system.lock'])
        self.assertIn('omadora app install steam', menu['install.gaming.steam']['action'])
        self.assertNotIn('setup.bad', menu)
        self.assertNotRegex(json.dumps(menu), r'\b(yay|pacman|paru)\b')

    def test_backup_restore_preserves_later_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            adapter.write(home / '.config/hypr/original', 'old')
            adapter.write(home / adapter.FONT_CONFIG, 'original font preference')
            backup = home / '.local/state/omadora/backups/initial'
            adapter.backup_user(home, backup)
            adapter.write(home / '.config/hypr/original', 'edited')
            adapter.write(home / '.config/foot/new', 'created by install')
            adapter.write(home / adapter.FONT_CONFIG, 'new font preference')
            rescue = adapter.restore_user(home, backup)
            self.assertEqual((home / '.config/hypr/original').read_text(), 'old')
            self.assertEqual((rescue / '.config/hypr/original').read_text(), 'edited')
            self.assertFalse((home / '.config/foot').exists())
            self.assertEqual((home / adapter.FONT_CONFIG).read_text(), 'original font preference')
            self.assertEqual((rescue / adapter.FONT_CONFIG).read_text(), 'new font preference')

    def test_legacy_backup_remains_restorable(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            adapter.write(home / '.config/hypr/original', 'old')
            backup = home / 'backup'
            adapter.backup_user(home, backup)
            manifest = adapter.read_json(backup / 'manifest.json')
            adapter.write(backup / 'manifest.json', json.dumps([e for e in manifest if e['path'] != adapter.FONT_CONFIG]))
            adapter.write(home / '.config/hypr/original', 'edited')
            adapter.restore_user(home, backup)
            self.assertEqual((home / '.config/hypr/original').read_text(), 'old')

    def test_incomplete_backup_rejected_before_deleting_user_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            adapter.write(home / '.config/hypr/original', 'old')
            backup = home / 'backup'
            adapter.backup_user(home, backup)
            import shutil
            shutil.rmtree(backup / '.config/hypr')
            with self.assertRaises(ValueError):
                adapter.restore_user(home, backup)
            self.assertEqual((home / '.config/hypr/original').read_text(), 'old')

    def test_restore_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            adapter.write(home / 'backup/manifest.json', '[{"path":"../../outside", "existed":false}]')
            with self.assertRaises(ValueError):
                adapter.restore_user(home, home / 'backup')

    def test_restore_rejects_replaced_parent_before_deleting_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            outside = Path(tmp) / 'outside'
            adapter.write(home / '.config/hypr/original', 'original')
            backup = home / '.local/state/omadora/backups/initial'
            adapter.backup_user(home, backup)
            adapter.write(outside / 'conf.d/99-omadora.conf', 'unrelated font config')
            try:
                (home / '.config/fontconfig').symlink_to(outside, target_is_directory=True)
            except OSError as error:
                if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                    self.skipTest('Windows lacks symlink privilege; exercised in Linux CI')
                raise
            adapter.write(home / '.config/hypr/original', 'later edit')
            with self.assertRaisesRegex(ValueError, 'parent must not be a symlink'):
                adapter.restore_user(home, backup)
            self.assertEqual((outside / 'conf.d/99-omadora.conf').read_text(), 'unrelated font config')
            self.assertEqual((home / '.config/hypr/original').read_text(), 'later edit')

    def test_real_upstream_build(self):
        source = os.environ.get('OMADORA_TEST_UPSTREAM')
        if not source:
            self.skipTest('Set OMADORA_TEST_UPSTREAM to a v4.0.4 checkout')
        with tempfile.TemporaryDirectory() as tmp:
            output = adapter.assemble(Path(source), Path(tmp) / 'stage')
            tree = output / 'upstream'
            self.assertTrue((tree / 'shell/shell.qml').is_file())
            menu = adapter.read_json(tree / 'default/omarchy/omarchy-menu.jsonc')
            self.assertIn('install.gaming.steam', menu)
            self.assertIn('system.lock', menu)
            # Fedora-added entries must not reference removed upstream helpers.
            import re
            for entry in menu.values():
                for field in ('action', 'when', 'disabled', 'provider'):
                    for command in re.findall(r'\bomarchy-[a-z0-9-]+\b', str(entry.get(field, ''))):
                        self.assertTrue((tree / 'bin' / command).is_file(), command)
            self.assertNotIn('install.gaming.xbox-controllers', menu)
            self.assertIn('omarchy_preinstalled_bindings = false', (tree / 'config/hypr/hyprland.lua').read_text())
            self.assertFalse((tree / 'install').exists())
            self.assertNotIn('polkit-gnome', (tree / 'config/hypr/autostart.lua').read_text())
            self.assertTrue((tree / 'shell/plugins/polkit/PolkitAgent.qml').is_file())
            self.assertNotIn('FONTCONFIG_FILE', (output / 'system/omadora-env').read_text())
            self.assertIn('gtk-contained-dark.css', (output / 'share/themes/Adwaita-dark/gtk-3.0/gtk.css').read_text())
            self.assertIn('gsettings set', (tree / 'bin/omarchy-theme-set-gnome').read_text())
            logo = (tree / 'logo.txt').read_text(encoding='utf-8')
            self.assertEqual(logo, (tree / 'config/omarchy/branding/screensaver.txt').read_text(encoding='utf-8'))
            self.assertNotEqual(logo, (Path(source) / 'logo.txt').read_text(encoding='utf-8'))
            self.assertIn('Omadora menu', (tree / 'default/hypr/bindings/utilities.lua').read_text(encoding='utf-8'))
            self.assertIn('OMARCHY_PATH', (tree / 'config/hypr/hyprland.lua').read_text(encoding='utf-8'))
            self.assertEqual((tree / 'LICENSE').read_bytes(), (Path(source) / 'LICENSE').read_bytes())
            self.assertEqual(adapter.read_json(tree / 'config/omarchy/shell.json')['idle']['screensaver'], 150)
            report = adapter.read_json(output / 'portability-report.json')
            for command in report['blocked_commands']:
                self.assertIn('exit 1', (tree / 'bin' / command).read_text())
            for command in (tree / 'bin').iterdir():
                if command.is_file():
                    self.assertIsNone(adapter.DISALLOWED.search(command.read_text(encoding='utf-8')), command.name)

    def test_font_integrity(self):
        import hashlib
        font = ROOT / 'assets/fonts/JetBrainsMonoNLNerdFont-Regular.ttf'
        self.assertEqual(hashlib.sha256(font.read_bytes()).hexdigest(), 'efd0c812226247ba45bb31a816ec63876fb0d8d930dbb0e633770965fcc81081')
        self.assertIn('SIL OPEN FONT LICENSE', (ROOT / 'assets/fonts/OFL.txt').read_text())


if __name__ == '__main__':
    unittest.main()
