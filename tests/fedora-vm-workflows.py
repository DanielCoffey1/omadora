"""Interactive optional setup with real transactions in a disposable desktop."""
import json
from pathlib import Path
import subprocess
import time
import pexpect

out = Path('/tmp/omadora-vm-results/workflows')
out.mkdir(parents=True, exist_ok=True)
cli = ['python3', '/usr/local/share/omadora/omadora.py', 'app']
results = []


def present(key):
    return subprocess.run(cli + ['installed', key], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def transact(action, key, log, answers=None):
    answers = answers or {}
    child = pexpect.spawn(cli[0], cli[1:] + [action, key], encoding='utf-8', timeout=600,
                          env=__import__('os').environ | {'TERM': 'xterm-256color'})
    child.logfile_read = log
    patterns = [pexpect.EOF, r'\[[Yy]/[Nn]\]', r'\[[Nn]/[Yy]\]', *answers]
    try:
        while True:
            selected = child.expect(patterns)
            if selected == 0:
                break
            child.sendline('y' if selected < 3 else answers[patterns[selected]])
        child.close()
        assert child.exitstatus == 0, f'{action} {key} failed'
    finally:
        if child.isalive():
            child.close(force=True)


def clients():
    return json.loads(subprocess.check_output(['hyprctl', 'clients', '-j']))


def close_new(before):
    for client in clients():
        if client['address'] not in before:
            command = 'hl.dsp.window.close({window=' + json.dumps('address:' + client['address']) + '})'
            subprocess.run(['hyprctl', 'dispatch', command], check=True, stdout=subprocess.DEVNULL)


def launch(command, log):
    before = {c['address'] for c in clients()}
    process = subprocess.Popen(command, stdout=log, stderr=log)
    try:
        deadline = time.monotonic() + 60
        while not any(c['address'] not in before for c in clients()):
            assert time.monotonic() < deadline, 'Launcher did not create a window'
            time.sleep(2)
        time.sleep(15)
        return before
    except Exception:
        close_new(before)
        raise


subprocess.run(['gnome-keyring-daemon', '--unlock'], input='omadora-vm-test-only', text=True, capture_output=True, check=True)
for key in ('tui', 'copr-package', 'preinstalls', 'xbox-cloud', 'chromium-account'):
    record = {'workflow': key}
    with (out / (key + '.log')).open('w') as log:
        before = None
        try:
            if key == 'preinstalls':
                assert not present('fira') and not present('steam')
                child = pexpect.spawn(cli[0], cli[1:] + ['install', key], encoding='utf-8', timeout=600,
                                      env=__import__('os').environ | {'TERM': 'xterm-256color'})
                child.logfile_read = log
                child.expect('Select optional apps')
                catalog = json.loads(Path('/usr/local/share/omadora/apps.json').read_text())
                index = [k for k in catalog if k != 'preinstalls'].index('fira')
                child.send('\x1b[B' * index)
                time.sleep(1)
                child.send(' ')
                child.send('\r')
                while child.expect([pexpect.EOF, r'\[[Yy]/[Nn]\]', r'\[[Nn]/[Yy]\]']) != 0:
                    child.sendline('y')
                child.close()
                assert child.exitstatus == 0 and present('fira') and not present('steam'), 'Chooser did not install only the selected font'
                transact('remove', 'fira', log)
                record['interaction'] = 'Real Gum multi-select installed Fira; Steam remained absent'
            elif key == 'tui':
                transact('install', key, log, {'Launcher name:': 'Omadora CI TUI', 'Command and arguments': 'top'})
                entries = json.loads((Path.home() / '.local/share/omadora/optional/tui/launchers.json').read_text())
                assert len(entries) == 1
                before = launch(['gtk-launch', 'omadora-' + next(iter(entries))], log)
                record['interaction'] = 'Created and launched a real Foot/top desktop entry'
            elif key == 'copr-package':
                assert not present('ghostty')
                transact('install', key, log, {'COPR owner/project:': 'scottames/ghostty', 'Package names separated': 'ghostty'})
                assert present('ghostty')
                transact('remove', 'ghostty', log)
                record['interaction'] = 'Prompted COPR owner/project and package; real Ghostty transaction succeeded'
            else:
                transact('install', key, log)
                before = launch(['python3', '/usr/local/share/omadora/omadora_optional.py', 'launch', key], log)
                record['interaction'] = 'Browser launcher rendered; no account login or gaming session attempted'
            assert present(key)
            subprocess.run(['grim', str(out / (key + '.png'))], check=True)
            if before is not None:
                close_new(before)
                before = None
            transact('remove', key, log)
            assert not present(key)
            record['status'] = 'PASS'
        except Exception as error:
            record.update(status='FAIL', error=str(error))
        finally:
            if before is not None:
                close_new(before)
    results.append(record)
    (out / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(record), flush=True)
assert all(r['status'] == 'PASS' for r in results), results
