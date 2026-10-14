"""Hardware-aware Fedora graphics setup. No compositor or firmware overrides."""
import json
import os
from pathlib import Path
import re
import subprocess

VENDORS = {'1002': 'AMD', '8086': 'Intel', '10de': 'NVIDIA'}
MOK = '/etc/pki/akmods/certs/public_key.der'


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


def nvidia_branch(gpus):
    cards = [g for g in managed(gpus) if g['vendor'] == 'NVIDIA']
    if not cards:
        return None
    data = json.loads((Path(__file__).resolve().parent / 'assets/nvidia-pci.json').read_text())
    branches = []
    for card in cards:
        branch = next((name for name, ids in data['branches'].items() if card['device'] in ids), None)
        if branch is None:
            raise ValueError(f"NVIDIA PCI ID {card['device']} is not in the supported current/580xx tables. Older 470xx/390xx cards are not supported by this Hyprland desktop; no NVIDIA packages were changed.")
        branches.append(branch)
    # 580 also supports newer cards. One shared driver must support all GPUs.
    if '580xx' in branches:
        if any(g['device'] not in data['580_supported'] for g in cards):
            raise ValueError('These NVIDIA GPUs need incompatible driver branches; no shared supported driver can be selected.')
        return '580xx'
    return 'current'


def nvidia_packages(branch, gaming=True):
    if not branch:
        return []
    suffix = '-580xx' if branch == '580xx' else ''
    driver = 'xorg-x11-drv-nvidia' + suffix
    result = ['akmod-nvidia' + suffix, driver, driver + '-cuda', driver + '-power',
              'nvidia-gpu-firmware', 'kernel', 'kernel-devel', 'akmods', 'mokutil']
    if gaming:
        result += [driver + '-libs.i686', driver + '-cuda-libs.i686',
                   'vulkan-loader.i686', 'gamemode', 'gamemode.i686', 'mangohud', 'mangohud.i686']
    return result


def plan(gpus, gaming=True):
    branch = nvidia_branch(gpus)
    return {'hardware': gpus, 'mesa_packages': mesa_packages(gpus, gaming),
            'nvidia_branch': branch, 'nvidia_packages': nvidia_packages(branch, gaming),
            'gaming': gaming, 'nvidia_driver_automatic': bool(branch),
            'secure_boot': 'Enroll the akmods key at reboot if Secure Boot is enabled.' if branch else 'unchanged'}


def default_kernel(a):
    image = a.run('sudo', 'grubby', '--default-kernel', capture=True).stdout.strip()
    match = re.fullmatch(r'/boot/vmlinuz-([0-9][A-Za-z0-9._+-]*)', image)
    if not match:
        raise ValueError('Cannot identify the next-boot kernel; NVIDIA module build was not verified.')
    return match[1]


def enroll_key(a):
    enrolled = a.run('sudo', 'mokutil', '--test-key', MOK, capture=True, check=False)
    if enrolled.returncode == 0:
        return False
    print('Secure Boot needs the akmods signing key. Choose a temporary enrollment password below. '
          'At reboot select Enroll MOK, Continue, Yes and enter that password. '
          'The NVIDIA driver cannot load until enrollment is completed.', flush=True)
    # curl | bash leaves stdin at EOF. Give mokutil the controlling terminal;
    # never put a password in argv, an environment variable, or a log.
    try:
        terminal = open('/dev/tty', 'r')
    except OSError as error:
        raise ValueError('Secure Boot key enrollment needs an interactive terminal. Run the installer from a terminal.') from error
    with terminal:
        subprocess.run(['sudo', 'mokutil', '--import', MOK], stdin=terminal, check=True)
    return True


def verify_signing_key(a, kernel):
    # For PKCS#7 modules kmod's sig_key is the certificate serial number,
    # not its subjectKeyIdentifier. Compare the actual akmods certificate.
    key = a.run('modinfo', '-k', kernel, '-F', 'sig_key', 'nvidia', capture=True).stdout.strip()
    certificate = a.run('sudo', 'openssl', 'x509', '-inform', 'DER', '-in', MOK,
                        '-noout', '-serial', capture=True).stdout
    serial = re.search(r'^serial=([0-9a-fA-F]+)\s*$', certificate, re.MULTILINE)
    if (not re.fullmatch(r'(?:[0-9a-fA-F]{2}:)*[0-9a-fA-F]{2}', key) or not serial or
            int(key.replace(':', ''), 16) != int(serial[1], 16)):
        raise ValueError('NVIDIA module was not signed with the akmods enrollment key; setup is incomplete.')


def install_nvidia(a, gpus, gaming=True):
    branch = nvidia_branch(gpus)
    if not branch:
        return
    if Path('/usr/bin/nvidia-uninstall').exists():
        raise ValueError('An NVIDIA .run installation is present. Remove it using its uninstaller before installing RPM Fusion drivers.')
    suffix = '-580xx' if branch == '580xx' else ''
    driver = 'xorg-x11-drv-nvidia' + suffix
    for other in ('xorg-x11-drv-nvidia', 'xorg-x11-drv-nvidia-580xx',
                  'xorg-x11-drv-nvidia-470xx', 'xorg-x11-drv-nvidia-390xx'):
        if other != driver and a.run('rpm', '-q', other, capture=True, check=False).returncode == 0:
            raise ValueError(f'{other} conflicts with the detected GPU branch {branch}. Remove the conflicting driver before retrying; Omadora will not erase unrelated packages.')
    a.run('sudo', 'dnf', 'install', '-y', 'mokutil')
    boot = secure_boot()
    if boot == 'unknown':
        raise ValueError('Cannot determine Secure Boot state. NVIDIA driver installation stopped before changing the driver.')
    fedora = a.os_release()['VERSION_ID']
    for kind in ('free', 'nonfree'):
        a.run('sudo', 'dnf', 'install', '-y',
              f'https://download1.rpmfusion.org/{kind}/fedora/rpmfusion-{kind}-release-{fedora}.noarch.rpm')
    # Generate the signing key before the first akmod transaction starts.
    a.run('sudo', 'dnf', 'install', '-y', 'akmods')
    a.run('sudo', 'kmodgenca', '-a')
    pending = enroll_key(a) if boot == 'enabled' else False
    a.run('sudo', 'dnf', 'install', '--refresh', '-y', *nvidia_packages(branch, gaming))
    kernel = default_kernel(a)
    a.run('sudo', 'dnf', 'install', '-y', 'kernel-devel-' + kernel)
    print(f'Building NVIDIA {branch} modules for next-boot kernel {kernel}; please wait.', flush=True)
    # Force regeneration after key creation, even when an unsigned build exists.
    a.run('sudo', 'akmods', '--force', '--rebuild', '--kernels', kernel)
    module_version = a.run('modinfo', '-k', kernel, '-F', 'version', 'nvidia', capture=True).stdout.strip()
    package_version = a.run('rpm', '-q', '--qf=%{VERSION}', driver, capture=True).stdout.strip()
    if not module_version or module_version != package_version:
        raise ValueError(f'NVIDIA kernel module/userspace version mismatch ({module_version!r} / {package_version!r}). Do not reboot into Omadora until setup succeeds; inspect /var/cache/akmods/.')
    verify_signing_key(a, kernel)
    # RPM Fusion owns blacklists, DRM defaults and power-management presets.
    # Do not unload Nouveau, force NVIDIA as the desktop GPU, or stop the session.
    a.run('sudo', 'dracut', '--force', '--kver', kernel)
    print(f'NVIDIA {module_version} built and verified for {kernel}. Reboot to activate it.' +
          (' Secure Boot enrollment is pending: complete Enroll MOK at reboot.' if pending else ''), flush=True)


def setup(a, gaming=False, nvidia=False, dry_run=False):
    gpus = detect()
    report = plan(gpus, gaming)
    print(json.dumps(report, indent=2))
    if nvidia and not report['nvidia_branch']:
        raise ValueError('No supported NVIDIA display GPU detected (vfio-pci devices are excluded).')
    if not managed(gpus):
        print('No supported physical GPU found. Virtual and passthrough-owned devices are left alone.')
        return
    if dry_run:
        return
    a.preflight()
    common = mesa_packages(gpus, gaming) + ['vulkan-tools', 'pciutils', 'mokutil']
    a.run('sudo', 'dnf', 'install', '-y', *common)
    install_nvidia(a, gpus, gaming)
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
