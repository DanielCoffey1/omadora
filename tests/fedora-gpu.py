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

    def os_release(self):
        return {'VERSION_ID': '44'}

mode = sys.argv[1]
card = dict(pci='0000:01:00.0', vendor='NVIDIA', device='2684',
            subvendor='10de', subdevice='0000', driver='', boot_display=True)
cards = ([card | dict(device='1c82' if mode == '580xx' else '2684')]
         if mode != 'mesa' else [card | dict(vendor='AMD'), card | dict(vendor='Intel', pci='0000:00:02.0')])
if mode == '580xx':
    # RPM Fusion's builder reads real lspci, not our simulated Python PCI rows.
    # With no physical NVIDIA card it would default to kernel-open, which cannot
    # run on Pascal. Test the proprietary kernel tree required by this fixture.
    # This macro exists ONLY in this disposable container, never in installation.
    Path('/etc/rpm').mkdir(exist_ok=True)
    Path('/etc/rpm/macros.omadora-test').write_text('%global _without_kmod_nvidia_detect 1\n')


def container_kernel(a):
    # Container host runs Ubuntu. Build for a real installed Fedora kernel,
    # not the host's kernel; no physical NVIDIA hardware is fabricated.
    return subprocess.run(['rpm', '-q', '--qf=%{VERSION}-%{RELEASE}.%{ARCH}\n', 'kernel-core'],
                          text=True, capture_output=True, check=True).stdout.strip().splitlines()[-1]


with patch.object(gpu, 'detect', return_value=cards), patch.object(gpu, 'secure_boot', return_value='not-uefi'), patch.object(gpu, 'default_kernel', side_effect=container_kernel):
    gpu.setup(Adapter(), gaming=True)
if mode == 'mesa':
    subprocess.run(['rpm', '-q', *gpu.mesa_packages(cards, True)], check=True)
    subprocess.run(['vulkaninfo', '--summary'], check=True)
else:
    branch = gpu.nvidia_branch(cards)
    subprocess.run(['rpm', '-q', *gpu.nvidia_packages(branch)], check=True)
    kernel = container_kernel(None)
    signer = subprocess.run(['modinfo', '-k', kernel, '-F', 'signer', 'nvidia'], text=True, capture_output=True, check=True).stdout.strip()
    assert signer, 'Akmods must sign the real built module'
    license = subprocess.run(['modinfo', '-k', kernel, '-F', 'license', 'nvidia'], text=True, capture_output=True, check=True).stdout.strip()
    assert license == ('NVIDIA' if mode == '580xx' else 'Dual MIT/GPL'), license
    image = Path('/boot') / ('initramfs-' + kernel + '.img')
    assert image.stat().st_size > 0
    print('PASS: real NVIDIA RPMs, signed kernel module, matching userspace and initramfs:', branch, kernel, signer, license)
print('PASS: GPU package setup', mode, flush=True)
print('NOT TESTED: physical GPU rendering, firmware MOK enrollment, laptop suspend or game performance.')
