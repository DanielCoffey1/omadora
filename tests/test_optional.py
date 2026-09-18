import hashlib
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import omadora_optional as optional
import omadora_workflows as workflows
import omadora as adapter


class OptionalTests(unittest.TestCase):
    def test_optional_chooser_keeps_screen_visible_and_installs_selected_ids(self):
        result = subprocess.CompletedProcess([], 0, 'dictation | Dictation\n')
        with patch.object(workflows.subprocess, 'run', return_value=result) as picker, \
             patch.object(optional, 'run') as install:
            workflows.install('preinstalls', Path('unused'))
        self.assertEqual(picker.call_args.kwargs.get('stdout'), subprocess.PIPE)
        self.assertIsNone(picker.call_args.kwargs.get('stderr'))
        self.assertFalse(picker.call_args.kwargs.get('capture_output'))
        install.assert_called_once_with('python3', ROOT / 'omadora.py', 'app', 'install', 'dictation')

    def test_cancel_optional_chooser_installs_nothing(self):
        with patch.object(workflows.subprocess, 'run', return_value=subprocess.CompletedProcess([], 130, '')), \
             patch.object(optional, 'run') as install:
            workflows.install('preinstalls', Path('unused'))
            install.assert_not_called()

    def test_all_upstream_install_actions_have_a_fedora_mapping(self):
        upstream = os.environ.get('OMADORA_TEST_UPSTREAM')
        if not upstream:
            self.skipTest('Requires pinned upstream')
        original = adapter.load_menu(Path(upstream) / 'default/omarchy/omarchy-menu.jsonc')
        menu = adapter.menu_for_fedora(original, adapter.read_json(ROOT / 'apps.json'), [])
        replacements = {'install.aur': 'install.copr-package',
                        'install.development.docker-dbs': 'install.development.database'}
        core = {'install.browser.firefox', 'install.terminal.foot'}
        for key, item in original.items():
            if key.startswith('install.') and item.get('action') and key not in core:
                self.assertIn(replacements.get(key, key), menu, key)
        self.assertNotIn('install.preinstalls', adapter.packages())

    def test_catalog_recipes_are_pinned_and_references_exist(self):
        recipes = optional.recipes()
        for app in adapter.read_json(ROOT / 'apps.json').values():
            if app['source'] == 'optional':
                self.assertIn(app['recipe'], recipes)
        for key, recipe in recipes.items():
            if recipe['kind'] != 'workflow':
                self.assertTrue(recipe['url'].startswith('https://'), key)
                algorithm = 'sha256' if recipe.get('sha256') else 'sha512'
                self.assertRegex(recipe[algorithm], '^[0-9a-f]{' + str(64 if algorithm == 'sha256' else 128) + '}$')
            for tool in recipe.get('tools', []):
                self.assertIn('@', tool)
                self.assertNotIn('latest', tool)

    def test_download_rejects_tampering_and_deletes_bad_bytes(self):
        class Response(io.BytesIO):
            url = 'https://example.org/app'
        with tempfile.TemporaryDirectory() as tmp, patch('urllib.request.urlopen', return_value=Response(b'bad')):
            target = Path(tmp) / 'download'
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                optional.download({'url': Response.url, 'sha256': hashlib.sha256(b'good').hexdigest()}, target)
            self.assertFalse(target.exists())

    def test_archive_cannot_write_outside_install_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'bad.tar'
            with tarfile.open(archive, 'w') as tar:
                member = tarfile.TarInfo('../outside'); member.size = 3
                tar.addfile(member, io.BytesIO(b'bad'))
            with self.assertRaises(tarfile.FilterError):
                optional.extract_tar(archive, root / 'target')
            self.assertFalse((root / 'outside').exists())

    def test_launcher_quotes_arguments_and_refuses_foreign_files(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            optional.launcher('test', 'Test app', ['example', 'one two', '%x', '$HOME'])
            path = Path(tmp) / '.local/share/applications/omadora-test.desktop'
            text = path.read_text()
            self.assertIn('"one two"', text)
            self.assertIn('%%x', text)
            self.assertIn('\\\\$HOME', text)
            path.write_text('[Desktop Entry]\nName=My app\n')
            with self.assertRaisesRegex(ValueError, 'foreign launcher'):
                optional.launcher('test', 'Test', ['example'])

    @unittest.skipIf(os.name == 'nt', 'Linux file modes and symlinks')
    def test_install_remove_preserves_foreign_command_and_personal_data(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            root = Path(tmp)
            recipe = {'name': 'Test', 'kind': 'binary', 'command': 'test-app', 'url': 'https://example.org/app', 'sha256': '0' * 64}
            final = optional.location('test'); final.parent.mkdir(parents=True)
            def download(spec, target): target.write_bytes(b'#!/bin/sh\nexit 0\n')
            with patch.object(optional, 'download', side_effect=download):
                optional.asset_install('test', recipe)
            personal = root / '.config/test-app'; personal.mkdir(parents=True); (personal / 'settings').write_text('keep')
            (root / '.local/bin/test-app').write_text('# user replacement\n')
            optional.remove('test', recipe)
            self.assertFalse(final.exists())
            self.assertTrue(personal.exists())
            self.assertEqual((root / '.local/bin/test-app').read_text(), '# user replacement\n')

    @unittest.skipIf(os.name == 'nt', 'Linux symlinks')
    def test_redirected_storage_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            base = Path(tmp) / '.local/share/omadora'; base.mkdir(parents=True)
            outside = Path(tmp) / 'outside'; outside.mkdir()
            (base / 'optional').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlinks'):
                optional.location('test')

    def test_databases_bind_only_loopback_and_keep_named_volumes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)), patch.object(workflows, 'deps'), patch.object(workflows, 'own_launcher'), patch.object(workflows.subprocess, 'run') as inspect, patch.object(optional, 'run') as run:
            inspect.return_value.returncode = 1
            workflows.database('db-postgres', Path(tmp))
            create = next(call.args for call in run.call_args_list if call.args[:2] == ('podman', 'create'))
            self.assertIn('127.0.0.1:5432:5432', create)
            self.assertIn('omadora-db-postgres-data:/var/lib/postgresql:Z', create)
            envfile = Path(tmp) / '.config/omadora/databases/postgres.env'
            self.assertIn('POSTGRES_PASSWORD=', envfile.read_text())
            self.assertNotIn('trust', str(create))
            if os.name != 'nt': self.assertEqual(envfile.stat().st_mode & 0o777, 0o600)

    def test_failed_registration_can_resume_without_download(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'home', return_value=Path(tmp)):
            recipe = {'name': 'Test', 'kind': 'binary', 'command': 'test-app'}
            final = optional.location('test'); final.parent.mkdir(parents=True)
            command = Path(tmp) / '.local/bin/test-app'; command.parent.mkdir(parents=True)
            command.write_text('# existing user command')
            with patch.object(optional, 'download', side_effect=lambda spec, target: target.write_bytes(b'payload')) as download:
                with self.assertRaisesRegex(ValueError, 'not owned'):
                    optional.asset_install('test', recipe)
                self.assertFalse((final / 'installed.json').exists())
                self.assertTrue((final / 'pending.json').exists())
                command.unlink()
                optional.asset_install('test', recipe)
                self.assertEqual(download.call_count, 1)
            self.assertTrue((final / 'installed.json').is_file())
            self.assertFalse((final / 'pending.json').exists())
            optional.remove('test', recipe)
            self.assertFalse(final.exists())


if __name__ == '__main__':
    unittest.main()
