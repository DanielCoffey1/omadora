"""Hardware-aware Fedora graphics setup. No compositor or firmware overrides."""
import json
import os
from pathlib import Path
import re
import subprocess

VENDORS = {'1002': 'AMD', '8086': 'Intel', '10de': 'NVIDIA'}


def read(path, default=''):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def detect(root=Path('/sys/bus/pci/devices')):
    result = []
    for path in sorted(Path(root).glob('*')):
        if not re.fullmatch(r'[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]', path.name):
            continue
        if not read(path / 'class').startswith('0x03'):
            continue
        vendor = read(path / 'vendor').removeprefix('0x').lower()
        result.append({'pci': path.name, 'vendor': VENDORS.get(vendor, vendor),
                       'device': read(path / 'device').removeprefix('0x').lower(),
                       'subvendor': read(path / 'subsystem_vendor').removeprefix('0x').lower(),
                       'subdevice': read(path / 'subsystem_device').removeprefix('0x').lower(),
                       'driver': (path / 'driver').resolve().name if (path / 'driver').is_symlink() else '',
                       'boot_display': read(path / 'boot_vga') == '1'})
    return result


def managed(gpus):
    return [g for g in gpus if g['vendor'] in VENDORS.values() and g['driver'] != 'vfio-pci']


def mesa_packages(gpus, gaming=False):
    vendors = {g['vendor'] for g in managed(gpus)}
    packages = []
    if vendors & {'AMD', 'Intel'}:
        packages += ['mesa-dri-drivers.x86_64', 'mesa-vulkan-drivers.x86_64', 'vulkan-loader.x86_64']
        if gaming:
            packages += ['mesa-dri-drivers.i686', 'mesa-vulkan-drivers.i686',
                         'mesa-libGL.i686', 'mesa-libEGL.i686', 'vulkan-loader.i686']
    for vendor, package in (('AMD', 'amd-gpu-firmware'), ('Intel', 'intel-gpu-firmware')):
        if vendor in vendors:
            packages.append(package)
    return packages


def probe(*args):
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=20)
        return {'status': p.returncode, 'output': (p.stdout + p.stderr).strip()}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {'status': None, 'output': str(e)}


def secure_boot():
    if not Path('/sys/firmware/efi').exists():
        return 'not-uefi'
    result = probe('mokutil', '--sb-state')
    if result['status'] == 0:
        if 'SecureBoot enabled' in result['output']:
            return 'enabled'
        if 'SecureBoot disabled' in result['output']:
            return 'disabled'
    return 'unknown'


def status():
    gpus = detect()
    for g in gpus:
        g['description'] = probe('lspci', '-D', '-s', g['pci'])['output']
    vulkan = probe('vulkaninfo', '--summary')
    return {'gpus': gpus, 'secure_boot': secure_boot(),
            'vulkan': vulkan, 'acceleration': acceleration(vulkan),
            'nvidia': probe('nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'),
            'nvidia_drm_modeset': read('/sys/module/nvidia_drm/parameters/modeset', 'not loaded'),
            'note': 'A successful Vulkan probe may be software rendering. Check deviceName/deviceType; CPU/llvmpipe is not GPU acceleration.'}


def acceleration(result):
    if result['status'] != 0:
        return 'unverified: Vulkan probe unavailable or failed'
    if re.search(r'deviceType\s*=\s*PHYSICAL_DEVICE_TYPE_(?:DISCRETE|INTEGRATED)_GPU', result['output']):
        return 'hardware Vulkan device detected; game performance not tested'
    return 'no physical Vulkan GPU confirmed (software/virtual rendering or unrecognized output)'


def print_status():
    report = status()
    print('Graphics hardware')
    for g in report['gpus']:
        print(f"  {g['pci']}  {g['vendor']} [{g['device']}]  driver={g['driver'] or 'not loaded'}")
        print('   ', g['description'])
    print('Secure Boot:', report['secure_boot'])
    print('Acceleration:', report['acceleration'])
    for key in ('vulkan', 'nvidia'):
        print(f"\n{key} (exit={report[key]['status']}):\n{report[key]['output']}")
    print('\nNVIDIA DRM modeset:', report['nvidia_drm_modeset'])
    print(report['note'])


def setup(a, gaming=False, nvidia=False, dry_run=False):
    # Keep the old flag as an explicit error for existing installations/scripts.
    # Reject it before detection, repository changes or privileged operations.
    if nvidia:
        raise ValueError('NVIDIA driver installation is managed manually. Install your driver outside Omadora, then reboot and use omadora gpu status.')
    gpus = detect()
    print(json.dumps({'hardware': gpus, 'mesa_packages': mesa_packages(gpus, gaming),
                      'gaming': gaming, 'nvidia_driver_automatic': False}, indent=2))
    if not managed(gpus):
        print('No supported physical GPU found. Virtual and passthrough-owned devices are left alone.')
        return
    if dry_run:
        return
    a.preflight()
    common = mesa_packages(gpus, gaming) + ['vulkan-tools', 'pciutils', 'mokutil']
    a.run('sudo', 'dnf', 'install', *common)
    if any(g['vendor'] == 'NVIDIA' for g in managed(gpus)):
        print('NVIDIA detected. Omadora leaves your driver unchanged; manage NVIDIA drivers and gaming libraries yourself.')
    print('Fedora graphics libraries installed. Run omadora gpu status in the desktop to check acceleration.')


def launch(command, pci=None):
    if not command:
        raise ValueError('Supply an application after --, for example: omadora gpu run -- steam')
    gpus = managed(detect())
    # boot_vga is not a reliable integrated/discrete classifier (MUX modes can
    # make a dedicated card the boot GPU). Do not guess between Mesa devices.
    if pci:
        choices = [g for g in gpus if g['pci'] == pci]
    elif len(gpus) == 1:
        choices = gpus
    else:
        choices = [g for g in gpus if g['vendor'] == 'NVIDIA']
    if len(choices) != 1:
        raise ValueError('Choose one GPU with --pci ADDRESS; see omadora gpu status.')
    gpu = choices[0]
    env = os.environ.copy()
    for key in ('DRI_PRIME', '__NV_PRIME_RENDER_OFFLOAD', '__GLX_VENDOR_LIBRARY_NAME', '__VK_LAYER_NV_optimus'):
        env.pop(key, None)
    if gpu['vendor'] == 'NVIDIA':
        if gpu['driver'] != 'nvidia':
            raise ValueError('The NVIDIA driver is not active. Complete setup/reboot and check GPU status.')
        if sum(g['vendor'] == 'NVIDIA' for g in gpus) > 1:
            raise ValueError('Multiple NVIDIA offload devices need explicit provider configuration; automatic selection is unavailable.')
        env.update({'__NV_PRIME_RENDER_OFFLOAD': '1', '__GLX_VENDOR_LIBRARY_NAME': 'nvidia',
                    '__VK_LAYER_NV_optimus': 'NVIDIA_only'})
    else:
        if gpu['driver'] not in ('amdgpu', 'radeon', 'i915', 'xe'):
            raise ValueError('The selected GPU has no supported active kernel driver; check GPU status first.')
        env['DRI_PRIME'] = 'pci-' + gpu['pci'].replace(':', '_').replace('.', '_')
    os.execvpe(command[0], command, env)
