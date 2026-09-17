#!/usr/bin/python3
"""Resolve optional apps in the disposable Fedora test system; install none."""
import importlib.util
from pathlib import Path
import subprocess
import sys

spec = importlib.util.spec_from_file_location('omadora', '/src/omadora.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
apps = adapter.read_json('/src/apps.json')

# Only the disposable test fixture enables these repositories up front.
for command in adapter.app_commands(apps['steam'], 'install')[:-1]:
    subprocess.run([*command[:3], '-y', *command[3:]], check=True)

packages = sorted({package for app in apps.values() for package in app.get('packages', [])})
result = subprocess.run(['sudo', 'dnf', '--assumeno', 'install', *packages], text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(__import__('os').environ, LC_ALL='C'))
print(result.stdout, flush=True)
Path('/tmp/omadora-app-resolution.txt').write_text(result.stdout)
if result.returncode not in (0, 1) or (result.returncode == 1 and 'Operation aborted by the user' not in result.stdout):
    sys.exit('Optional RPM transaction did not resolve successfully')

subprocess.run(['flatpak', 'remote-add', '--user', '--if-not-exists', 'flathub',
                'https://flathub.org/repo/flathub.flatpakrepo'], check=True)
listing = subprocess.run(['flatpak', 'remote-ls', '--user', '--app', '--columns=application', 'flathub'],
                         text=True, stdout=subprocess.PIPE, check=True).stdout
available = set(listing.splitlines())
missing = [app['id'] for app in apps.values() if app['source'] == 'flatpak' and app['id'] not in available]
if missing:
    sys.exit('Unavailable Flatpak IDs: ' + ', '.join(missing))
print(f'PASS: {len(apps)} optional apps resolve in Fedora/RPM Fusion/Flathub; none installed.')
