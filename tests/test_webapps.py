import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'assets/omarchy-launch-webapp'


class WebappTests(unittest.TestCase):
    def launch(self, browsers, *args):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp)
            for name in browsers:
                path = bin_dir / name
                path.write_text('#!/bin/bash\nexit 0\n')
                path.chmod(0o755)
            uwsm = bin_dir / 'uwsm-app'
            uwsm.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
            uwsm.chmod(0o755)
            return subprocess.run(['/bin/bash', str(LAUNCHER), *args],
                                  env={**os.environ, 'PATH': tmp},
                                  text=True, capture_output=True)

    def test_brave_origin_matches_local_launcher_and_preserves_arguments(self):
        url = 'https://example.com/?q=hello world&next=$HOME'
        result = self.launch(['brave-origin-stable', 'chromium-browser'],
                             url, '--profile-directory=Profile 2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            '--', 'brave-origin-stable', '--app=' + url,
            '--profile-directory=Profile 2'])

    def test_native_brave_and_fedora_chromium_use_app_mode(self):
        for browser in ('brave-browser-stable', 'brave-browser', 'chromium-browser', 'chromium'):
            with self.subTest(browser=browser):
                result = self.launch([browser], 'https://example.com')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [
                    '--', browser, '--app=https://example.com'])

    def test_missing_browser_explains_how_to_restore_support(self):
        result = self.launch([], 'https://example.com')
        self.assertEqual(result.returncode, 1)
        self.assertIn('sudo dnf install chromium', result.stderr)

    def test_missing_url_does_not_launch_browser(self):
        result = self.launch(['chromium-browser'])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
