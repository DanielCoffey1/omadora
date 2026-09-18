#!/usr/bin/env python3
"""Collect read-only Fedora/Omadora diagnostics; never infer workload passes."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def probe(argv, timeout=15):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
                                env=os.environ | {'LC_ALL': 'C'})
        return {'status': 'ok' if result.returncode == 0 else 'error',
                'returncode': result.returncode, 'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip()}
    except FileNotFoundError:
        return {'status': 'unavailable'}
    except subprocess.TimeoutExpired:
        return {'status': 'timeout'}
    except OSError as error:
        return {'status': 'error', 'error_type': type(error).__name__}


def monitor_probe():
    result = probe(['hyprctl', '-j', 'monitors', 'all'])
    if result['status'] != 'ok':
        return {'status': result['status']}
    # Exclude monitor serials, active-window titles and other session details.
    fields = ('name', 'make', 'model', 'width', 'height', 'refreshRate', 'x', 'y',
              'scale', 'transform', 'disabled', 'dpmsStatus', 'vrr', 'availableModes')
    try:
        monitors = json.loads(result['stdout'])
        if not isinstance(monitors, list) or any(not isinstance(m, dict) for m in monitors):
            raise ValueError('Invalid monitor list')
        return {'status': 'ok', 'monitors': [{k: m[k] for k in fields if k in m} for m in monitors]}
    except (ValueError, TypeError):
        return {'status': 'invalid_json'}


def read_value(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def classify_virtualization(result):
    if result.get('returncode') == 1 and result.get('stdout') == 'none':
        return 'no_virtualization_detected'
    if result.get('status') == 'ok' and result.get('stdout') not in ('', 'none'):
        return 'virtualized'
    return 'unknown'


CHECKS = {
    'login': 'Log out and select Omadora in GDM; log in with your password. Repeat after reboot.',
    'graphics': 'Open Firefox and Foot, resize/move/fullscreen windows, and play a local video. Record glitches or stalls.',
    'displays': 'For each available display, record connector, resolution, refresh and scaling. Test moving windows between displays and unplug/replug of an external display.',
    'wifi': 'If present, connect to Wi-Fi and load a web page; disconnect/reconnect and repeat. Do not record the network password or SSID.',
    'audio': 'Test speaker/headphone output, volume/mute, and microphone recording/playback with the devices you have.',
    'bluetooth': 'If present, pair your own headset or controller and reconnect it after a logout/reboot.',
    'suspend': 'Save work. Use the normal Omadora lock/suspend flow locally. Wake, confirm the lock remains, unlock, then check displays/network/audio. Repeat three cycles, recording each separately.',
    'recovery': 'After the other tests, follow docs/MAINTENANCE.md from GNOME to test configuration restore, preserving the displayed backup/rescue paths.',
}


def collect():
    commands = {
        'virtualization': ['systemd-detect-virt'],
        'selinux': ['getenforce'],
        'secure_boot': ['mokutil', '--sb-state'],
        'pci_drivers': ['lspci', '-nnk'],
        'network_devices': ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'device', 'status'],
        'rfkill': ['rfkill', '--output', 'TYPE,SOFT,HARD', '--noheadings'],
        'hyprland_version': ['hyprctl', 'version'],
        'nvidia': ['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'],
        'packages': ['rpm', '-q', 'fedora-release-workstation', 'kernel-core', 'hyprland',
                     'quickshell', 'mesa-dri-drivers', 'akmod-nvidia', 'xorg-x11-drv-nvidia'],
    }
    probes = {name: probe(argv) for name, argv in commands.items()}
    probes['monitors'] = monitor_probe()
    return {
        'schema_version': 1,
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Diagnostic inventory only; no hardware acceptance tests were executed.',
        'environment': classify_virtualization(probes['virtualization']),
        'os_release': read_value('/etc/os-release'),
        'omadora_release': read_value('/usr/local/share/omadora/release.json'),
        'kernel': platform.release(), 'architecture': platform.machine(),
        'firmware': 'UEFI' if Path('/sys/firmware/efi').is_dir() else 'non-UEFI-or-unavailable',
        'hardware': {name: read_value('/sys/class/dmi/id/' + name)
                     for name in ('sys_vendor', 'product_name', 'board_name')},
        'sleep_modes': read_value('/sys/power/mem_sleep'),
        'session': {name: os.environ.get(name) for name in ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP')},
        'probes': probes,
        'manual_checks': {name: {'status': 'not_tested', 'notes': ''} for name in CHECKS},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New report directory; existing directories are refused')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Run this from the physical Fedora machine, inside your Omadora session.')
    if os.geteuid() == 0:
        parser.error('Run as your regular desktop user without sudo.')
    output = args.output or Path('omadora-hardware-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    report = collect()
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Omadora hardware test record', '',
             'Inventory collected. Every acceptance check below is NOT TESTED.',
             'Record PASS, FAIL or NOT APPLICABLE only after doing the check.',
             'A VM result does not establish physical hardware support.', '']
    for name, instructions in CHECKS.items():
        lines += [f'## {name}', '', instructions, '', 'Status: NOT TESTED', 'Notes:', '']
    lines += ['For suspend, record cycles 1, 2 and 3 individually. A single successful wake is insufficient.',
              'Review this folder before sharing; nothing is uploaded automatically.', '']
    (output / 'checklist.md').write_text('\n'.join(lines))
    print(f'Inventory saved to {output.resolve()}')
    print(f'Environment: {report["environment"]}; all hardware acceptance checks remain NOT TESTED.')


if __name__ == '__main__':
    main()
