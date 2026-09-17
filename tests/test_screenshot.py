"""Failure and cancellation behavior without a compositor; UI is tested in Fedora."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'assets/scripts/capture-screenshot'


@unittest.skipIf(os.name == 'nt', 'Linux shell regression tests run in CI')
class ScreenshotTests(unittest.TestCase):
    def test_save_copy_cancel_and_capture_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / 'bin'
            fake.mkdir()
            commands = {
                'omarchy-capture-region': 'printf "%s\\n" "${TEST_FREEZE_PID:-}"; [ "$TEST_CANCEL" = 0 ] || exit 1; echo "0,0 100x80"',
                'grim': 'printf PNGDATA > "$3"; exit "$TEST_GRIM_STATUS"',
                'wl-copy': 'cat > "$TEST_CLIPBOARD"',
                'notify-send': ':',
            }
            for name, body in commands.items():
                path = fake / name
                path.write_text('#!/bin/sh\n' + body + '\n')
                path.chmod(0o755)
            pictures = root / 'Pictures with spaces'
            clipboard = root / 'clipboard'
            env = os.environ | {'HOME': str(root), 'PATH': str(fake) + ':' + os.environ['PATH'],
                                'OMARCHY_SCREENSHOT_DIR': str(pictures), 'TEST_CLIPBOARD': str(clipboard),
                                'TEST_CANCEL': '0', 'TEST_GRIM_STATUS': '0'}
            def capture(*args, check=True):
                return subprocess.run(['bash', str(SCRIPT), *args], env=env,
                                      check=check, capture_output=True, timeout=10)
            capture('fullscreen')
            files = list(pictures.glob('*.png'))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_bytes(), clipboard.read_bytes())
            capture('fullscreen', 'copy')
            self.assertEqual(list(pictures.glob('*.png')), files)
            env['TEST_GRIM_STATUS'] = '1'
            self.assertNotEqual(capture('fullscreen', check=False).returncode, 0)
            self.assertEqual(list(pictures.glob('*.png')), files, 'Failed capture must remove its partial PNG')
            env['TEST_CANCEL'] = '1'
            freeze = subprocess.Popen(['sleep', '30'])
            try:
                env['TEST_FREEZE_PID'] = str(freeze.pid)
                capture()
                freeze.wait(timeout=3)
                self.assertEqual(list(pictures.glob('*.png')), files)
            finally:
                if freeze.poll() is None:
                    freeze.kill()
                    freeze.wait()
