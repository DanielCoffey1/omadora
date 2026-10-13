"""Disposable container only: real Fedora packages, simulated PCI IDs."""
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

assert Path('/run/.containerenv').exists() or Path('/.dockerenv').exists(), 'Container required'
sys.path.insert(0, '/src')
import omadora_gpu as gpu


class Adapter:
    def run(self, *args, capture=False, check=True):
        args = list(map(str, args))
        if args[0] == 'sudo':
            args.pop(0)
        if args[:2] == ['dnf', 'install']:
            args.insert(2, '-y')
        print('RUN', args, flush=True)
        return subprocess.run(args, text=True, capture_output=capture, check=check)

    def preflight(self):
        pass  # The disposable container deliberately substitutes for a desktop user.

mode = sys.argv[1]
card = dict(pci='0000:01:00.0', vendor='NVIDIA', device='2684',
            subvendor='10de', subdevice='0000', driver='', boot_display=True)
cards = [card] if mode == 'nvidia-manual' else [card | dict(vendor='AMD'), card | dict(vendor='Intel', pci='0000:00:02.0')]
with patch.object(gpu, 'detect', return_value=cards):
    if mode == 'nvidia-manual':
        from unittest.mock import Mock
        adapter = Mock()
        try:
            gpu.setup(adapter, gaming=True, nvidia=True)
        except ValueError as error:
            assert 'managed manually' in str(error)
        else:
            raise AssertionError('NVIDIA setup must be rejected')
        adapter.run.assert_not_called()
        adapter.preflight.assert_not_called()
    gpu.setup(Adapter(), gaming=True)
if mode == 'mesa':
    subprocess.run(['rpm', '-q', *gpu.mesa_packages(cards, True)], check=True)
    subprocess.run(['vulkaninfo', '--summary'], check=True)
else:
    installed = subprocess.run(['rpm', '-qa', '--qf=%{NAME}\n'], text=True, capture_output=True, check=True).stdout.splitlines()
    assert not any(name.startswith(('akmod-nvidia', 'xorg-x11-drv-nvidia', 'rpmfusion-')) for name in installed)
print('PASS: GPU package setup', mode, flush=True)
print('NOT TESTED: physical GPU rendering, laptop suspend or game performance.')
