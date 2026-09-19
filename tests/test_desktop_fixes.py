import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_adapter', ROOT / 'omadora.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class DesktopFixTests(unittest.TestCase):
    def test_app_logos_match_across_install_remove_and_keep_theme_rendering(self):
        brands = adapter.read_json(ROOT / 'assets/icons/brands.json')
        apps = adapter.read_json(ROOT / 'apps.json')
        menu = adapter.menu_for_fedora({}, apps, [])
        for app_id, slug in brands['apps'].items():
            self.assertIn(app_id, apps)
            for action in ('install', 'remove'):
                key = '.'.join(filter(None, (action, apps[app_id]['category'], app_id)))
                entry = menu[key]
                self.assertEqual(entry['icon'], chr(brands['icons'][slug]['codepoint']))
                self.assertEqual(entry['iconFont'], brands['family'])
                self.assertNotIn('color', entry)
        self.assertNotEqual(menu['install.browser.brave']['icon'], menu['install.browser.chrome']['icon'])
        self.assertEqual(menu['install.browser.chromium']['icon'], menu['install.browser.chrome']['icon'])
        # These names have unrelated travel/fashion marks in logo collections.
        self.assertNotIn('tui', brands['apps'])
        self.assertNotIn('hermes', brands['apps'])

    def test_update_refreshes_bar_after_success_and_failure(self):
        for failure in (False, True):
            calls = []
            def run(*args, **kwargs):
                calls.append(args)
                if args[0] == 'sudo' and failure:
                    raise subprocess.CalledProcessError(1, args)
                return subprocess.CompletedProcess(args, 0)
            with patch.object(sys, 'argv', ['omadora', 'update']), \
                 patch.object(adapter, 'preflight'), patch.object(adapter, 'run', side_effect=run), \
                 patch.object(adapter.shutil, 'which', return_value='/usr/bin/omarchy-shell'):
                if failure:
                    with self.assertRaises(subprocess.CalledProcessError):
                        adapter.main()
                else:
                    adapter.main()
            self.assertEqual(calls, [('sudo', 'dnf', 'upgrade', '--refresh'),
                                    ('omarchy-shell', '-q', 'omarchy.system-update', 'refresh')])

    def test_update_check_distinguishes_errors_from_no_updates(self):
        for dnf_status, status in ((100, 0), (0, 1), (1, 2)):
            with patch.object(sys, 'argv', ['omadora', 'updates-available']), \
                 patch.object(adapter, 'run', return_value=subprocess.CompletedProcess([], dnf_status)):
                self.assertEqual(adapter.main(), status)

    def test_all_install_remove_entries_have_icons(self):
        menu = adapter.menu_for_fedora({}, adapter.read_json(ROOT / 'apps.json'), [])
        for key, entry in menu.items():
            if key.startswith(('install.', 'remove.')):
                self.assertTrue(entry.get('icon'), key)
        self.assertIn('trigger.capture.screenrecord.stop', menu)

    def test_package_picker_deduplicates_and_limits_selection_to_inventory(self):
        inventory = subprocess.CompletedProcess([], 0, 'vim\nbash\nvim\n--bad\n', '')
        selection = subprocess.CompletedProcess([], 0, 'vim\nbash\nvim\n', '')
        with patch.object(adapter, 'run', return_value=inventory) as query, \
             patch.object(adapter.subprocess, 'run', return_value=selection) as picker:
            self.assertEqual(adapter.choose_packages('remove'), ['vim', 'bash'])
            self.assertEqual(query.call_args.args[0], 'rpm')
            self.assertIn('--multi', picker.call_args.args[0])
            self.assertEqual(picker.call_args.kwargs['input'], 'bash\nvim')
        selection.stdout = 'not-in-inventory\n'
        with patch.object(adapter, 'run', return_value=inventory), patch.object(adapter.subprocess, 'run', return_value=selection):
            with self.assertRaises(ValueError):
                adapter.choose_packages('install')

    def test_cancel_never_yields_a_package_transaction(self):
        with patch.object(adapter, 'run', return_value=subprocess.CompletedProcess([], 0, 'vim\n', '')), \
             patch.object(adapter.subprocess, 'run', return_value=subprocess.CompletedProcess([], 130, '', '')):
            self.assertEqual(adapter.choose_packages('install'), [])
        self.assertNotIn('-y', adapter.package_commands('remove', ['vim', 'bash']))

    @unittest.skipIf(os.name == 'nt', 'Linux terminal helper')
    def test_terminal_action_preserves_error_status_and_arguments(self):
        helper = ROOT / 'assets/scripts/terminal-action'
        result = subprocess.run(['bash', str(helper), 'bash', '-c', 'printf "%s" "$1"; exit 7', '_', 'name with spaces'],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, 'name with spaces')

    @unittest.skipIf(os.name == 'nt', 'Linux recorder ownership')
    def test_recording_state_cannot_stop_unrelated_process(self):
        import importlib.machinery
        loader = importlib.machinery.SourceFileLoader('screenrecord_test', str(ROOT / 'assets/scripts/screenrecord'))
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(module)
        import json
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            state.write_text(json.dumps({'pid': os.getpid(), 'start': module.identity(os.getpid()), 'file': __file__}))
            self.assertIsNone(module.active(state))
            state.write_text('{invalid')
            self.assertIsNone(module.active(state))
