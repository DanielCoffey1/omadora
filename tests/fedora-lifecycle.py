"""Real transactions, process interruption and recovery in disposable Fedora."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

source = Path(__file__).resolve().parents[1]
home = Path.home()
prefix = Path('/usr/local/share/omadora')
state = home / '.local/state/omadora'
results = []


def run(*args, success=True):
    result = subprocess.run([str(a) for a in args], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=900)
    print(result.stdout, flush=True)
    if success:
        assert result.returncode == 0, result.stdout
    else:
        assert result.returncode != 0, 'Expected interrupted/failed transaction'
    return result


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


if sys.argv[1] == 'install':
    for relative in ('.config/hypr/original', '.local/share/fonts/omadora/original.txt'):
        path = home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('pre-install sentinel')
    run('python3', source / 'tests/lifecycle-interrupt.py', 'install', success=False)
    assert (state / 'transaction.json').exists() and prefix.exists()
    # Verify restoration actually writes dconf even from a shell without a bus.
    saved = json.loads((Path(json.loads((state / 'transaction.json').read_text())['backup']) / 'desktop-settings.json').read_text())
    changed = 'prefer-light' if saved['color-scheme'] != "'prefer-light'" else 'prefer-dark'
    run('dbus-run-session', '--', 'gsettings', 'set', 'org.gnome.desktop.interface', 'color-scheme', changed)
    run('python3', source / 'omadora.py', 'recover')
    for key, expected in saved.items():
        assert subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.interface', key], text=True).strip() == expected
    assert not prefix.exists() and not (state / 'transaction.json').exists()
    assert not Path('/usr/local/bin/omadora').is_symlink()
    assert not Path('/usr/share/wayland-sessions/omadora.desktop').exists()
    assert not Path('/etc/pam.d/omarchy-lock-password').exists()
    for relative in ('.config/hypr/original', '.local/share/fonts/omadora/original.txt'):
        assert (home / relative).read_text() == 'pre-install sentinel'
    run('python3', source / 'omadora.py', 'recover')  # no-op is safe
    results.append('PASS: SIGKILL during first install; recovered system/config/font files; repeat recovery is safe')
else:
    # Distinguish old/new deployed trees even when testing the same source ref.
    run('sudo', 'touch', prefix / 'previous-release-marker')
    before = hashes(prefix)
    config = home / '.config/hypr/hyprland.lua'
    original = config.read_text()
    # Invalid user Lua must reject the new desktop and leave those user edits.
    config.write_text(original + '\nthis is not valid lua !!!\n')
    run('python3', source / 'omadora.py', 'upgrade', '--local', success=False)
    assert before == hashes(prefix), 'Failed config validation did not roll back runtime'
    assert config.read_text().endswith('this is not valid lua !!!\n')
    assert not (state / 'transaction.json').exists()
    config.write_text(original)
    results.append('PASS: invalid personal Lua rejected upgrade and restored prior runtime without erasing edits')

    run('python3', source / 'tests/lifecycle-interrupt.py', 'upgrade', success=False)
    assert (state / 'transaction.json').exists()
    # An edit after the interruption must also survive recovery.
    marker = home / '.config/foot/after-interruption.txt'
    marker.write_text('keep this edit')
    run('python3', source / 'omadora.py', 'recover')
    assert before == hashes(prefix)
    assert marker.read_text() == 'keep this edit'
    results.append('PASS: SIGKILL during upgrade; recovered old runtime and retained subsequent personal edits')

    user_before = {name: hashes(home / name) for name in (
        '.config/hypr', '.config/foot', '.config/omarchy', '.local/state/omarchy', '.local/share/fonts/omadora')}
    settings = subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'])
    revision = json.loads((prefix / 'release.json').read_text())['revision']
    run('/usr/local/bin/omadora', 'upgrade', '--ref', revision)
    assert not (prefix / 'previous-release-marker').exists()
    assert user_before == {name: hashes(home / name) for name in user_before}
    assert settings == subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'])
    assert json.loads((state / 'installation.json').read_text())['status'] == 'installed'
    assert not (state / 'transaction.json').exists()
    run('python3', source / 'omadora.py', 'recover')
    results.append('PASS: real desktop upgrade verified Hyprland config and preserved personal files/theme/font')
    run('/usr/local/bin/omadora', 'rollback')
    assert before == hashes(prefix)
    assert user_before == {name: hashes(home / name) for name in user_before}
    results.append('PASS: installed rollback command restored previous desktop and retained user configuration')

output = Path('/tmp/omadora-lifecycle-' + sys.argv[1] + '.json')
output.write_text(json.dumps(results, indent=2))
print('\n'.join(results), flush=True)
