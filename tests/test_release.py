"""Release defaults stay pinned; development install commands explicitly opt in."""
import importlib.util
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_adapter', ROOT / 'omadora.py')
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


class ReleaseTests(unittest.TestCase):
    def test_bootstrap_uses_same_release_as_adapter(self):
        default = re.search(r'ref=\$\{OMADORA_REF:-([^}]+)\}', (ROOT / 'boot.sh').read_text()).group(1)
        self.assertEqual(default, adapter.RELEASE_REF)
        self.assertRegex(default, r'^v\d+\.\d+\.\d+-alpha$')
        for name in ('README.md', 'docs/QUICKSTART.md', 'docs/MAINTENANCE.md',
                     f'docs/releases/{default}.md'):
            with self.subTest(document=name):
                contents = (ROOT / name).read_text(encoding='utf-8')
                refs = re.findall(r'raw.githubusercontent.com/DanielCoffey1/omadora/([^/]+)/boot.sh', contents)
                self.assertTrue(refs, 'Document must include an installation or recovery command')
                development_docs = ('README.md', 'docs/QUICKSTART.md')
                expected = {default, 'main'} if name in development_docs else {default}
                self.assertEqual(set(refs), expected)
                for line in contents.splitlines():
                    if 'raw.githubusercontent.com/DanielCoffey1/omadora/main/boot.sh' in line:
                        self.assertRegex(line, r'\|\s*OMADORA_REF=main\s+bash\s*$',
                                         'Development installs must explicitly select main')

    def test_cli_upgrade_defaults_to_release_and_allows_explicit_override(self):
        lifecycle = Mock()
        with patch.object(adapter, 'lifecycle', return_value=lifecycle):
            with patch.object(sys, 'argv', ['omadora', 'upgrade']):
                adapter.main()
            self.assertEqual(lifecycle.upgrade.call_args.args[2], adapter.RELEASE_REF)
            with patch.object(sys, 'argv', ['omadora', 'upgrade', '--ref', 'main']):
                adapter.main()
            self.assertEqual(lifecycle.upgrade.call_args.args[2], 'main')

    def test_lifecycle_fetches_release_when_ref_omitted(self):
        lifecycle = adapter.lifecycle()
        fake = Mock(RELEASE_REF=adapter.RELEASE_REF)
        with patch.object(lifecycle, 'offline'):
            lifecycle.upgrade(fake)
        fetches = [c.args for c in fake.run.call_args_list if 'fetch' in c.args]
        self.assertEqual(len(fetches), 1)
        self.assertEqual(fetches[0][-1], adapter.RELEASE_REF)
