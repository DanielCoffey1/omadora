"""Real catalog transactions and basic launch checks in the disposable VM.

No accounts are signed into and no games or third-party projects are run.
Window creation is only a launch smoke test, not complete application QA.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import pexpect

out = Path('/tmp/omadora-vm-results/apps')
out.mkdir(parents=True, exist_ok=True)
catalog = json.loads(Path('/usr/local/share/omadora/apps.json').read_text())
cli = ['python3', '/usr/local/share/omadora/omadora.py', 'app']
results = []
gui = {'steam': ['steam'], 'lutris': ['lutris'], 'gimp': ['gimp'],
       'libreoffice': ['libreoffice', '--writer'], 'kitty': ['kitty'],
       'alacritty': ['alacritty'], 'chromium': ['chromium', '--no-first-run']}
terminal = {'mangohud': ['mangohud', '--version'], 'gamemode': ['gamemoded', '--version'],
            'podman': ['podman', 'info'], 'node': ['node', '--version'],
            'rust': ['rustc', '--version'], 'go': ['go', 'version']}


def installed(app_id):
    return subprocess.run(cli + ['installed', app_id], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def windows():
    return json.loads(subprocess.check_output(['hyprctl', 'clients', '-j']))


def transaction(action, app_id, log):
    # A terminal matters: Flatpak intentionally rejects noninteractive prompts,
    # and successive DNF processes must not consume each other's buffered input.
    child = pexpect.spawn(cli[0], cli[1:] + [action, app_id], encoding='utf-8', timeout=600)
    child.logfile_read = log
    try:
        while True:
            match = child.expect([r'\[[Yy]/[Nn]\]', r'\[[Nn]/[Yy]\]', pexpect.EOF])
            if match == 2:
                break
            child.sendline('y')
        child.close()
        return child.exitstatus
    finally:
        if child.isalive():
            child.close(force=True)


for app_id, app in catalog.items():
    record = {'app': app_id, 'source': app['source'], 'preexisting': installed(app_id)}
    print('Testing app:', app_id, flush=True)
    with (out / f'{app_id}.log').open('w') as log:
        process = None
        try:
            # Answer the same interactive prompts a user sees. No adapter or
            # package-manager shim replaces the real transaction.
            status = transaction('install', app_id, log)
            assert status == 0 and installed(app_id), 'installation failed'
            record['install'] = 'PASS'
            if app_id in terminal:
                p = subprocess.run(terminal[app_id], stdout=log, stderr=log, timeout=60)
                assert p.returncode == 0, 'CLI smoke failed'
                record['launch'] = 'PASS: CLI smoke'
            else:
                before = {c['address'] for c in windows()}
                command = ['flatpak', 'run', app['id']] if app['source'] == 'flatpak' else gui[app_id]
                process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
                deadline = time.monotonic() + 75
                created = []
                while time.monotonic() < deadline:
                    created = [c for c in windows() if c['address'] not in before]
                    if created:
                        break
                    time.sleep(2)
                assert created, 'no application window appeared in 75 seconds'
                record['windows'] = [{'class': c['class'], 'title': c['title']} for c in created]
                time.sleep(3)
                subprocess.run(['grim', str(out / f'{app_id}.png')], stdout=log, stderr=log, timeout=30)
                record['launch'] = 'PASS: window created'
        except Exception as error:
            record['error'] = str(error)
        finally:
            if app['source'] == 'flatpak':
                subprocess.run(['flatpak', 'kill', app['id']], stdout=log, stderr=log, timeout=20)
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if not record['preexisting']:
                try:
                    status = transaction('remove', app_id, log)
                    assert status == 0 and not installed(app_id), 'removal failed'
                    record['remove'] = 'PASS'
                except Exception as error:
                    record['remove'] = 'FAIL: ' + str(error)
            else:
                record['remove'] = 'NOT RUN: present in base Workstation/dependencies'
    results.append(record)
    (out / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(record), flush=True)
    # Keep the growing thin disk and package caches bounded in CI.
    subprocess.run(['sudo', 'dnf', 'clean', 'packages'], stdout=subprocess.DEVNULL)
print('Catalog transactions complete.', flush=True)
