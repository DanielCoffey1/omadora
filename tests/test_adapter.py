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
    def test_desktop_recovery_without_bus_verifies_persisted_values(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp)
            values = dict(zip(adapter.DESKTOP_KEYS, ("'prefer-dark'", "'Adwaita-dark'", "'Yaru-blue'")))
            adapter.write(backup / 'desktop-settings.json', json.dumps(values))
            stored, commands = {}, []
            def run(*args, **kwargs):
                commands.append(args)
                if args[0] == 'dbus-run-session':
                    stored[args[-2]] = args[-1]
                    return SimpleNamespace(returncode=0)
                return SimpleNamespace(stdout=stored[args[-1]] + '\n')
            with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'is_socket', return_value=False), patch.object(adapter, 'run', side_effect=run):
                adapter.desktop_settings('restore', backup)
            self.assertEqual(stored, values)
            self.assertEqual(sum(c[0] == 'dbus-run-session' for c in commands), 3)
            with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'is_socket', return_value=False), patch.object(adapter, 'run', return_value=SimpleNamespace(stdout="'unchanged'\n")):
                with self.assertRaisesRegex(ValueError, 'was not restored'):
                    adapter.desktop_settings('restore', backup)

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

    def test_steam_certificate_alias_preserves_existing_trust(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bundle, alias = home / 'bundle.pem', home / 'cert.pem'
            with patch.object(adapter, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'bundle is missing'):
                    adapter.steam_certificates(bundle, alias)
                run.assert_not_called()
                adapter.write(bundle, 'maintained roots')
                adapter.steam_certificates(bundle, alias)
                run.assert_called_once_with('sudo', 'ln', '-s', bundle, alias)
                run.reset_mock()
                adapter.write(alias, 'administrator roots')
                adapter.steam_certificates(bundle, alias)
                run.assert_not_called()
                self.assertEqual(alias.read_text(), 'administrator roots')

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
            adapter.write(backup / 'manifest.json', json.dumps([e for e in manifest if e['path'] not in (adapter.FONT_CONFIG, '.local/share/fonts/omadora')]))
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
            utilities = (tree / 'default/hypr/bindings/utilities.lua').read_text()
            for unsupported in ('omarchy-agent', 'omarchy-transcode', 'omarchy-reminder', 'toggle share', 'tui = "btop"'):
                self.assertNotIn(unsupported, utilities)
            self.assertIn('tui = "top"', utilities)
            for unsupported in ('learn.tmux-keybindings', 'trigger.hardware.hybrid-gpu', 'trigger.toggle.crash-capture', 'style.about'):
                self.assertNotIn(unsupported, menu)
            self.assertNotIn('$HOME/.config/fontconfig/fonts.conf', (tree / 'bin/omarchy-font-set').read_text(encoding='utf-8'))
            self.assertIn('$HOME/' + adapter.FONT_CONFIG, (tree / 'bin/omarchy-font-set').read_text(encoding='utf-8'))
            self.assertIn('github.com/DanielCoffey1/omadora', menu['learn.omarchy']['action'])
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

    @unittest.skipIf(os.name == 'nt', 'Generated Linux session is executed in Linux CI')
    def test_session_activation_failure_stops_compositor(self):
        import subprocess
        source = os.environ.get('OMADORA_TEST_UPSTREAM')
        if not source:
            self.skipTest('Set OMADORA_TEST_UPSTREAM to the pinned checkout')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = adapter.assemble(Path(source), root / 'stage')
            fake = root / 'bin'
            adapter.write(fake / 'loginctl', '''#!/bin/sh
printf '%s\\n' "$*" >> "$TEST_TRACE"
case "$1" in
  activate) exit "$TEST_ACTIVATE_STATUS" ;;
  show-session) echo yes ;;
esac
''', 0o755)
            adapter.write(fake / 'uwsm', '#!/bin/sh\nprintf started >> "$TEST_STARTED"\n', 0o755)
            trace, started = root / 'trace', root / 'started'
            env = os.environ | {'PATH': str(fake) + ':' + os.environ['PATH'],
                                'XDG_SESSION_ID': 'test-session', 'XDG_SEAT': 'seat0',
                                'TEST_TRACE': str(trace), 'TEST_STARTED': str(started),
                                'TEST_ACTIVATE_STATUS': '1'}
            command = ['bash', str(stage / 'bin/omadora-session')]
            failed = subprocess.run(command, env=env, capture_output=True, timeout=15)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(started.exists())
            self.assertIn('activate test-session', trace.read_text())
            env['TEST_ACTIVATE_STATUS'] = '0'
            subprocess.run(command, env=env, check=True, capture_output=True, timeout=15)
            self.assertEqual(started.read_text(), 'started')
            trace.unlink()
            env.pop('XDG_SEAT')
            subprocess.run(command, env=env, check=True, capture_output=True, timeout=15)
            self.assertFalse(trace.exists(), 'Do not activate a remote or seatless session')


if __name__ == '__main__':
    unittest.main()
