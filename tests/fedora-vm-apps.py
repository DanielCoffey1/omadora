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
import atexit
import shutil
import re
from PIL import Image, ImageStat

out = Path('/tmp/omadora-vm-results/apps')
out.mkdir(parents=True, exist_ok=True)
catalog = json.loads(Path('/usr/local/share/omadora/apps.json').read_text())
cli = ['python3', '/usr/local/share/omadora/omadora.py', 'app']
results = []
selection_file = Path(__file__).with_name('selected-apps.json')
probes = json.loads(Path(__file__).with_name('catalog-smoke.json').read_text())
selection = json.loads(selection_file.read_text()) if selection_file.exists() else list(probes)
probes.update(json.loads(Path(__file__).with_name('optional-smoke.json').read_text()))
assert selection and set(selection) <= set(catalog)
(out / 'selection.json').write_text(json.dumps(selection))
with (out / 'environment.log').open('w') as log:
    subprocess.run(['lscpu'], stdout=log, stderr=log)
    subprocess.run(['rpm', '-q', 'hyprland', 'aquamarine', 'mesa-dri-drivers', 'glibc'], stdout=log, stderr=log)
# Long unattended downloads should not auto-lock over app screenshots. This
# exercises the normal Stay Awake control and restores it when the suite exits.
subprocess.run(['omarchy-shell', 'idle', 'disable'], check=True)
assert not json.loads(subprocess.check_output(['omarchy-shell', 'idle', 'status']))['enabled']
atexit.register(lambda: subprocess.run(['omarchy-shell', 'idle', 'enable']))
assert set(selection) <= set(probes), 'Use optional-assets or workflow-specific checks for optional recipes'


def installed(app_id):
    return subprocess.run(cli + ['installed', app_id], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def windows():
    return json.loads(subprocess.check_output(['hyprctl', 'clients', '-j']))


def app_window(app_id, window):
    # A setup dialog, updater, keyring prompt or splash is not the application.
    aliases = {'protonup': 'pupgui2', 'obs': 'obsproject', 'libreoffice': 'libreoffice',
               'vscode': 'code', 'brave-origin': 'brave', 'geforce-now': 'geforcenow',
               '1password': 'onepassword', 'grok-bot': 'grok'}
    app_class = window['class'].lower()
    title = window['title'].lower()
    if app_id == 'chrome' and title == 'google chrome and chromeos additional terms of service':
        return True
    if app_id == 'dropbox' and 'dropbox' in title and app_class in ('org.mozilla.firefox', 'chromium', 'chromium-browser'):
        return True
    normalize = lambda value: re.sub('[^a-z0-9]', '', value.lower())
    return (normalize(aliases.get(app_id, app_id)) in normalize(app_class)
            and not any(part in title for part in ('startup', 'updater', 'steam setup')))


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


for app_id in selection:
    app = catalog[app_id]
    record = {'app': app_id, 'source': app['source'], 'preexisting': installed(app_id)}
    if probes[app_id].get('fixture_note'):
        record['fixture_note'] = probes[app_id]['fixture_note']
    print('Testing app:', app_id, flush=True)
    with (out / f'{app_id}.log').open('w') as log:
        process = None
        before = None
        try:
            # Answer the same interactive prompts a user sees. No adapter or
            # package-manager shim replaces the real transaction.
            status = transaction('install', app_id, log)
            assert status == 0 and installed(app_id), 'installation failed'
            record['install'] = 'PASS'
            if app_id == 'steam':
                bundle = Path('/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem')
                assert Path('/etc/pki/tls/cert.pem').resolve() == bundle
                assert b'BEGIN CERTIFICATE' in bundle.read_bytes()
                assert not (Path.home() / '.local/share/applications/steam.desktop').exists()
            if app['source'] == 'flatpak':
                fonts = subprocess.run(['flatpak', 'run', '--command=fc-match', app['id'], 'sans'],
                                       text=True, capture_output=True, timeout=30)
                log.write(fonts.stdout + fonts.stderr)
                assert fonts.returncode == 0 and 'Fontconfig error' not in fonts.stderr, 'sandbox font lookup failed'
                record['fonts'] = 'PASS: sandbox font lookup'
            if probes[app_id]['kind'] in ('cli', 'font'):
                p = subprocess.run(probes[app_id]['command'], text=True, capture_output=True, timeout=60)
                log.write(p.stdout + p.stderr)
                if probes[app_id]['kind'] == 'font':
                    assert probes[app_id]['expected'] in p.stdout.lower(), 'Requested font resolved to fallback'
                assert p.returncode == 0, 'CLI smoke failed'
                record['launch'] = 'PASS: CLI smoke'
            else:
                before = {c['address'] for c in windows()}
                command = probes[app_id]['command']
                process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
                deadline = time.monotonic() + (300 if app_id == 'steam' else 90)
                created = []
                acknowledged = False
                while time.monotonic() < deadline:
                    if app_id == 'signal' and not acknowledged:
                        warning = next((c for c in windows() if c['address'] not in before
                                        and c['class'] == 'zenity' and c['title'] == 'Warning'), None)
                        if warning:
                            # Disposable empty profile only: exercise the wrapper's
                            # Yes choice without linking an account or changing
                            # the product's storage configuration.
                            subprocess.run(['grim', str(out / 'signal-wrapper.png')], timeout=30)
                            # Zenity focuses No initially. Move right to Yes first.
                            for key in ('Right', 'Return'):
                                for state in ('down', 'up'):
                                    expression = 'hl.dsp.send_key_state({mods="", key="' + key + '", state="' + state + '", window="address:' + warning['address'] + '"})'
                                    subprocess.run(['hyprctl', 'dispatch', expression], stdout=log, stderr=log, check=True)
                                    time.sleep(.1)
                            acknowledged = True
                            record['fixture_warning_acknowledged'] = True
                    created = [c for c in windows() if c['address'] not in before and app_window(app_id, c)]
                    if created:
                        break
                    time.sleep(2)
                if not created:
                    record['observed_windows'] = [{'class': c['class'], 'title': c['title']}
                                                  for c in windows() if c['address'] not in before]
                    subprocess.run(['grim', str(out / f'{app_id}.png')], stdout=log, stderr=log, timeout=30)
                assert created, 'no matching application window appeared before timeout'
                record['windows'] = [{'class': c['class'], 'title': c['title']} for c in created]
                time.sleep(30 if app_id in ('discord', 'signal', 'steam', 'vscode', 'zed', 'minecraft') else 5)
                if app_id in ('vscode', 'zed'):
                    # A mapped but blank editor is not a successful launch.
                    deadline = time.monotonic() + 60
                    while True:
                        client = next(c for c in windows() if c['address'] == created[0]['address'])
                        x, y = client['at']
                        width, height = client['size']
                        crop = out / f'{app_id}-window.png'
                        subprocess.run(['grim', '-g', f'{x},{y} {width}x{height}', str(crop)], check=True, timeout=30)
                        if max(ImageStat.Stat(Image.open(crop).convert('RGB')).stddev) > 3:
                            break
                        assert time.monotonic() < deadline, 'Editor window stayed blank'
                        time.sleep(5)
                if app_id == 'vscode':
                    # First run opens an optional sign-in welcome modal.
                    # Dismiss it without connecting any account.
                    for state in ('down', 'up'):
                        expression = 'hl.dsp.send_key_state({mods="", key="Escape", state="' + state + '", window="address:' + created[0]['address'] + '"})'
                        subprocess.run(['hyprctl', 'dispatch', expression], stdout=log, stderr=log, check=True)
                    time.sleep(2)
                    for state in ('down', 'up'):
                        expression = 'hl.dsp.send_key_state({mods="CTRL", key="n", state="' + state + '", window="address:' + created[0]['address'] + '"})'
                        subprocess.run(['hyprctl', 'dispatch', expression], stdout=log, stderr=log, check=True)
                    deadline = time.monotonic() + 30
                    while not any(c['class'].lower() == 'code' and 'untitled' in c['title'].lower() for c in windows()):
                        assert time.monotonic() < deadline, 'VS Code did not respond to New File'
                        time.sleep(2)
                    record['interaction'] = 'PASS: Ctrl+N opened an untitled editor'
                subprocess.run(['grim', str(out / f'{app_id}.png')], stdout=log, stderr=log, timeout=30)
                if app_id == 'geforce-now' and any('cannot continue' in c['title'].lower() for c in created):
                    record['launch'] = 'NOT VERIFIED: virtual GPU lacks Vulkan video decoding'
                    record['vm_limitation'] = 'GeForce NOW native client returned a graphics initialization error; installation/removal coverage only.'
                elif app_id == 'chrome' and any('Additional Terms of Service' in c['title'] for c in created):
                    record['launch'] = 'USER ACTION: Chrome terms dialog rendered; terms were not accepted'
                elif app_id == 'dropbox':
                    record['launch'] = 'PASS: Dropbox account setup opened; synchronization requires an account'
                else:
                    assert not any('unsupported gpu' in c['title'].lower() or 'cannot continue' in c['title'].lower() for c in windows() if c['address'] not in before), 'Application reported a runtime startup error'
                    record['launch'] = 'PASS: window created'
        except Exception as error:
            record['error'] = str(error)
        finally:
            if before is not None:
                for client in windows():
                    if client['address'] not in before:
                        expression = 'hl.dsp.window.close({ window = "address:' + client['address'] + '" })'
                        subprocess.run(['hyprctl', 'dispatch', expression], stdout=log, stderr=log, check=True)
                time.sleep(2)
            if app_id == 'steam':
                steam_logs = Path.home() / '.local/share/Steam/logs'
                if steam_logs.is_dir():
                    shutil.copytree(steam_logs, out / 'steam-client-logs', dirs_exist_ok=True)
                record['process_exit'] = process.poll() if process else None
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
