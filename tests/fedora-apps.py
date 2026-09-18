#!/usr/bin/python3
"""Resolve optional apps in the disposable Fedora test system; install none."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

spec = importlib.util.spec_from_file_location('omadora', '/src/omadora.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
apps = adapter.read_json('/src/apps.json')

# Exercise restored launcher creation/removal using the installed helpers.
# No browser/account or network request is needed for an installed icon name.
runtime = Path('/usr/local/share/omadora')
env = dict(os.environ, PATH=f'{runtime}/bin:{runtime}/upstream/bin:' + os.environ['PATH'],
           OMARCHY_REMOVE_NOTIFY='false')
launcher = Path.home() / '.local/share/applications/Omadora installer test.desktop'
subprocess.run(['omarchy-webapp-install', 'Omadora installer test',
                'https://example.org/?source=omadora&test=1', 'web-browser'], env=env, check=True)
assert launcher.is_file()
subprocess.run(['desktop-file-validate', str(launcher)], check=True)
assert 'Exec=omarchy-launch-webapp ' in launcher.read_text()
subprocess.run(['omarchy-webapp-remove', 'Omadora installer test'], env=env, check=True)
assert not launcher.exists()
subprocess.run(['file', '--version'], check=True, stdout=subprocess.DEVNULL)
print('PASS: installed web-app launcher creation, desktop-file validation and removal.')

# Only the disposable test fixture enables these repositories up front.
repositories = set()
for app in apps.values():
    if app['source'] not in ('rpmfusion', 'copr', 'vendor'):
        continue
    for command in adapter.app_commands(app, 'install')[:-1]:
        if tuple(command) not in repositories:
            prepared = [*command[:2], '-y', *command[2:]] if command[1] == 'dnf' else command
            subprocess.run(prepared, check=True)
            repositories.add(tuple(command))

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
print(f'PASS: {len(apps)} optional apps resolve in Fedora/RPM Fusion/COPR/vendor RPM/Flathub; none installed.')
