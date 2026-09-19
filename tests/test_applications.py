import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import omadora_applications as apps
import omadora as adapter


class ApplicationRefreshTests(unittest.TestCase):
    def test_offline_and_unresponsive_shell_do_not_fail_refresh(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('shell', 3)):
            with patch.object(apps.subprocess, 'run', side_effect=error):
                apps.refresh()

    def test_package_transaction_refreshes_even_after_partial_failure(self):
        for failed in (False, True):
            with patch.object(sys, 'argv', ['omadora', 'package', 'install', 'gedit']), \
                 patch.object(adapter, 'run', side_effect=subprocess.CalledProcessError(1, 'dnf') if failed else None), \
                 patch.object(apps, 'refresh') as refresh:
                if failed:
                    with self.assertRaises(subprocess.CalledProcessError):
                        adapter.main()
                else:
                    adapter.main()
                refresh.assert_called_once()

    def test_dry_run_does_not_refresh(self):
        with patch.object(sys, 'argv', ['omadora', 'package', 'install', 'gedit', '--dry-run']), \
             patch.object(apps, 'refresh') as refresh:
            adapter.main()
            refresh.assert_not_called()
