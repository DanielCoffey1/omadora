#!/usr/bin/python3
"""Resolve optional apps in the disposable Fedora test system; install none."""
import importlib.util
import ast
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

# Metadata signing keys use DNF's separate repository keyring. Import through
# the normal signed metadata refresh before the intentionally declined install.
subprocess.run(['sudo', 'dnf', '-y', 'makecache', '--refresh'], check=True)

packages = sorted({package for app in apps.values() for package in app.get('packages', [])})
optional = adapter.read_json('/src/optional.json')
dependencies = {p for recipe in optional.values() for p in recipe.get('dependencies', [])}
# Also resolve literal Fedora dependencies in interactive workflows, without
# starting services, connecting accounts, building a kernel driver or a VM.
for node in ast.walk(ast.parse(Path('/src/omadora_workflows.py').read_text())):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'deps':
        dependencies.update(arg.value for arg in node.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str))
packages = sorted(set(packages) | dependencies)
result = subprocess.run(['sudo', 'dnf', '--assumeno', 'install', *packages], text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(__import__('os').environ, LC_ALL='C'))
print(result.stdout, flush=True)
Path('/tmp/omadora-app-resolution.txt').write_text(result.stdout)
if result.returncode not in (0, 1) or (result.returncode == 1 and 'Operation aborted by the user' not in result.stdout):
    sys.exit('Optional RPM transaction did not resolve successfully')

missing = []
remotes = {app.get('remote', 'flathub'): app.get('remote_url', 'https://flathub.org/repo/flathub.flatpakrepo')
           for app in apps.values() if app['source'] == 'flatpak'}
for remote, url in remotes.items():
    subprocess.run(['flatpak', 'remote-add', '--user', '--if-not-exists', remote, url], check=True)
    listing = subprocess.run(['flatpak', 'remote-ls', '--user', '--app', '--columns=application', remote],
                             text=True, stdout=subprocess.PIPE, check=True).stdout
    available = set(listing.splitlines())
    missing.extend(app['id'] for app in apps.values() if app['source'] == 'flatpak'
                   and app.get('remote', 'flathub') == remote and app['id'] not in available)
if missing:
    sys.exit('Unavailable Flatpak IDs: ' + ', '.join(missing))
packaged = sum(app['source'] != 'optional' for app in apps.values())
print(f'PASS: {packaged} packaged apps and workflow RPM dependencies resolve; optional archives/workflows are tested separately. No catalog apps installed.')
