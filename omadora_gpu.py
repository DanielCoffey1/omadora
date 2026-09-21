"""Hardware-aware Fedora graphics setup. No compositor or firmware overrides."""
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

VENDORS = {'1002': 'AMD', '8086': 'Intel', '10de': 'NVIDIA'}
CERT = '/etc/pki/akmods/certs/public_key.der'


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


def supported_ids(html):
    # Read only Current, never the legacy tables later in the same document.
    current = re.search(r'id="Current".*?<table\b.*?</table>', html, re.S)
    if not current:
        raise ValueError('NVIDIA support-list format changed; driver installation stopped.')
    ids = set(re.findall(r'<tr id="devid([0-9A-Fa-f]{4}(?:_[0-9A-Fa-f]{4}_[0-9A-Fa-f]{4})?)"', current[0]))
    if not ids:
        raise ValueError('NVIDIA returned an empty support list.')
    return {x.lower() for x in ids}


def supports(gpu, ids):
    return gpu['device'] in ids or '_'.join((gpu['device'], gpu['subvendor'], gpu['subdevice'])) in ids


def candidate(a, suffix, gpus):
    package = 'akmod-nvidia' + suffix
    version = a.run('dnf', '-q', 'repoquery', '--available', '--latest-limit=1', '--arch=x86_64',
                    '--repo=rpmfusion-nonfree,rpmfusion-nonfree-updates', '--qf=%{version}\n',
                    package, capture=True).stdout.strip()
    if not re.fullmatch(r'\d+(?:\.\d+){1,3}', version):
        return None
    url = f'https://download.nvidia.com/XFree86/Linux-x86_64/{version}/README/supportedchips.html'
    with urllib.request.urlopen(url, timeout=30) as response:
        ids = supported_ids(response.read(2_000_001).decode('utf-8'))
    if all(supports(g, ids) for g in gpus):
        return suffix, version
    return None


def nvidia_packages(suffix, version, gaming):
    # Keep userspace and the akmod on the version whose support list was checked.
    packages = [f'akmod-nvidia{suffix}-{version}',
                f'xorg-x11-drv-nvidia{suffix}-{version}',
                f'xorg-x11-drv-nvidia{suffix}-cuda-{version}',
                f'xorg-x11-drv-nvidia{suffix}-libs-{version}-*.x86_64']
    if gaming:
        packages += [f'xorg-x11-drv-nvidia{suffix}-libs-{version}-*.i686', 'vulkan-loader.i686']
    return packages


def install_detected(a):
    """Prepare NVIDIA before a fresh desktop deployment; never hide failures."""
    if not any(g['vendor'] == 'NVIDIA' for g in managed(detect())):
        return False
    print('NVIDIA detected: automatically checking and installing compatible drivers and gaming libraries.', flush=True)
    if setup(a, gaming=True, nvidia=True) == 3:
        raise ValueError('NVIDIA setup is waiting for Secure Boot enrollment. Reboot, approve Enroll MOK with your enrollment password, then rerun the same Omadora installer command from GNOME or a TTY. The Omadora desktop has not been deployed.')
    return True


def setup(a, gaming=False, nvidia=False, dry_run=False):
    gpus = detect()
    usable = managed(gpus)
    print(json.dumps({'hardware': gpus, 'mesa_packages': mesa_packages(gpus, gaming),
                      'gaming': gaming, 'nvidia_requested': nvidia}, indent=2))
    if not usable:
        print('No supported physical GPU found. Virtual and passthrough-owned devices are left alone.')
        return
    cards = [g for g in usable if g['vendor'] == 'NVIDIA']
    if nvidia and not cards:
        raise ValueError('No NVIDIA display controller found.')
    if dry_run:
        if nvidia:
            print('Would enable RPM Fusion, verify current/580xx PCI support, check Secure Boot enrollment, install matched drivers and build modules. No changes made.')
        return
    a.preflight()
    # Module replacement is performed from GNOME/TTY, not a live Hyprland session.
    if nvidia:
        a.lifecycle().offline(a)
        if Path('/usr/bin/nvidia-uninstall').exists():
            raise ValueError('An NVIDIA .run installation is present; migrate it to RPM Fusion before using this setup.')
    common = mesa_packages(gpus, gaming) + ['vulkan-tools', 'pciutils', 'mokutil']
    a.run('sudo', 'dnf', 'install', *common)
    if cards and not nvidia:
        print('NVIDIA detected. For a verified driver choice, log out of Hyprland and run: omadora gpu setup --nvidia' + (' --gaming' if gaming else ''))
    if not nvidia:
        print('Fedora graphics libraries installed. Run omadora gpu status in the desktop to check acceleration.')
        return
    for kind in ('free', 'nonfree'):
        a.run('sudo', 'dnf', 'install', f'https://mirrors.rpmfusion.org/{kind}/fedora/rpmfusion-{kind}-release-44.noarch.rpm')
    selected = candidate(a, '', cards) or candidate(a, '-580xx', cards)
    if not selected:
        raise ValueError('No verified current or 580xx driver supports all detected NVIDIA GPUs. Legacy/mixed hardware needs manual review; no NVIDIA driver was installed.')
    suffix, version = selected
    installed = a.run('rpm', '-qa', '--qf=%{NAME}\n', capture=True).stdout.splitlines()
    allowed = 'akmod-nvidia' + suffix
    if any((name.startswith('akmod-nvidia') and name != allowed) or
           name.startswith(('nvidia-driver', 'cuda-drivers', 'kmod-nvidia-latest', 'dkms-nvidia')) for name in installed):
        raise ValueError('Another NVIDIA driver branch/provider is installed. Resolve that installation before continuing.')
    state = secure_boot()
    if state == 'unknown':
        raise ValueError('Cannot determine Secure Boot state. NVIDIA installation stopped.')
    a.run('sudo', 'dnf', 'install', 'akmods', 'kernel-devel-matched')
    if state == 'enabled':
        a.run('sudo', '/usr/sbin/kmodgenca', '-a')
        if a.run('mokutil', '--test-key', CERT, check=False, capture=True).returncode != 0:
            print('Secure Boot requires one firmware approval. Choose a temporary enrollment password now. Reboot, choose Enroll MOK → Continue → Yes, enter it, then rerun this same setup command. NVIDIA driver installation waits until enrollment is complete.', flush=True)
            a.run('sudo', 'mokutil', '--import', CERT)
            return 3
    a.run('sudo', 'dnf', 'install', *nvidia_packages(suffix, version, gaming))
    # Build for the latest installed kernel, whose matching headers were ensured.
    kernels = a.run('rpm', '-q', 'kernel-devel', '--qf=%{VERSION}-%{RELEASE}.%{ARCH}\n', capture=True).stdout.splitlines()
    if not kernels or any(not re.fullmatch(r'[A-Za-z0-9._+-]+', k) for k in kernels):
        raise ValueError('No valid matching kernel headers found. Do not reboot until the module build is resolved.')
    for kernel in kernels:
        a.run('sudo', 'akmods', '--force', '--rebuild', '--kernels', kernel, '--akmod', 'nvidia' + suffix)
        a.run('modinfo', '-k', kernel, 'nvidia', capture=True)
        if state == 'enabled' and not a.run('modinfo', '-k', kernel, '-F', 'signer', 'nvidia', capture=True).stdout.strip():
            raise ValueError('NVIDIA module is unsigned. Resolve signing before rebooting.')
        a.run('sudo', 'dracut', '--force', '--kver', kernel)
    print('NVIDIA packages and kernel modules are installed. Reboot to activate them, then run omadora gpu status. No reboot or firmware changes were performed automatically.')


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
