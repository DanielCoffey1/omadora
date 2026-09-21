"""Disposable container only: real Fedora packages/module builds, simulated PCI IDs."""
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
        if args[:2] == ['dnf', 'install'] and '-y' not in args:
            args.insert(2, '-y')
        if args[:2] == ['mokutil', '--test-key']:
            print('SIMULATED: firmware already trusts the locally generated certificate', flush=True)
            return subprocess.CompletedProcess(args, 0, '')
        if args[0] == 'dracut':
            # Container overlay filesystems have no bootable host root device.
            args.insert(1, '--no-hostonly')
        print('RUN', args, flush=True)
        return subprocess.run(args, text=True, capture_output=capture, check=check)

    def preflight(self):
        pass  # The disposable container deliberately substitutes for a desktop user.

    def lifecycle(self):
        return self

    def offline(self, adapter):
        assert not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')


mode = sys.argv[1]
card = dict(pci='0000:01:00.0', vendor='NVIDIA', device='1b80' if mode == 'legacy' else '2684',
            subvendor='10de', subdevice='0000', driver='', boot_display=True)
cards = [card] if mode != 'mesa' else [card | dict(vendor='AMD'), card | dict(vendor='Intel', pci='0000:00:02.0')]
with patch.object(gpu, 'detect', return_value=cards), patch.object(gpu, 'secure_boot', return_value='enabled' if mode == 'current' else 'disabled'):
    gpu.setup(Adapter(), gaming=True, nvidia=mode != 'mesa')
if mode == 'mesa':
    subprocess.run(['rpm', '-q', *gpu.mesa_packages(cards, True)], check=True)
    subprocess.run(['vulkaninfo', '--summary'], check=True)
else:
    suffix = '-580xx' if mode == 'legacy' else ''
    subprocess.run(['rpm', '-q', 'akmod-nvidia' + suffix, 'xorg-x11-drv-nvidia' + suffix + '-libs.i686'], check=True)
    assert Path('/usr/sbin/kmodgenca').is_file()
    subprocess.run(['akmods', '--help'], check=True)
print('PASS: GPU package setup', mode, flush=True)
print('NOT TESTED: physical GPU rendering, firmware MOK approval, hardware suspend or game performance.')
