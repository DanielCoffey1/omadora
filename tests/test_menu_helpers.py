import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('menu_adapter', ROOT / 'omadora.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


@unittest.skipIf(os.name == 'nt', 'Execute generated Bash helpers in Linux CI')
class MenuHelperTests(unittest.TestCase):
    def test_interactive_helpers_without_perl(self):
        source = os.environ.get('OMADORA_TEST_UPSTREAM')
        if not source:
            self.skipTest('Pinned upstream checkout required')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            stage = adapter.assemble(source, base / 'stage')
            fake = base / 'bin'
            adapter.write(fake / 'perl', '#!/bin/sh\nexit 97\n', 0o755)
            adapter.write(fake / 'omarchy-shell', '''#!/usr/bin/python3
import json, os, pathlib, sys
assert sys.argv[1:4] == ['shell', 'summon', 'omarchy.menu']
payload = json.loads(sys.argv[4])
pathlib.Path(os.environ['PAYLOAD']).write_text(json.dumps(payload))
if os.environ['CANCEL'] != '1':
    pathlib.Path(payload['selectionFile']).write_text('selected ✓')
pathlib.Path(payload['doneFile']).touch()
''', 0o755)
            env = os.environ | {'PATH': str(fake) + ':' + os.environ['PATH'],
                                'OMARCHY_PATH': str(stage / 'upstream'),
                                'PAYLOAD': str(base / 'payload.json')}
            for kind in ('select', 'input'):
                for cancel in ('0', '1'):
                    with self.subTest(kind=kind, cancel=cancel):
                        command = ['bash', str(stage / 'upstream/bin' / ('omarchy-menu-' + kind)), 'Guide "✓"']
                        command += ['--', '--width', '800', '--height', '500'] if kind == 'select' else ['--width', '800']
                        options = ['SUPER + K → Keybindings', '\tTerminal\tQuotes " and \\']
                        p = subprocess.run(command, input='\n'.join(options), text=True,
                                           capture_output=True, env=env | {'CANCEL': cancel}, timeout=10)
                        self.assertEqual(p.returncode, int(cancel), p.stderr)
                        self.assertEqual(p.stdout, 'selected ✓' if cancel == '0' else '')
                        payload = json.loads((base / 'payload.json').read_text())
                        self.assertEqual(payload['prompt'], 'Guide "✓"')
                        self.assertEqual(payload['width'], 800)
                        if kind == 'select':
                            self.assertEqual(payload['options'], options)
                            self.assertEqual(payload['maxHeight'], 500)
                        for key in ('doneFile', 'selectionFile'):
                            self.assertFalse(Path(payload[key]).exists())
