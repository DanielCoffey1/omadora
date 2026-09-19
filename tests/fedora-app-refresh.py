"""Real Gio and patched Quickshell app library; no compositor restart required."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

PREFIX = Path('/usr/local/share/omadora')
with tempfile.TemporaryDirectory(prefix='omadora-app-refresh-') as tmp:
    base = Path(tmp)
    home = base / 'home'
    home.mkdir()
    config = base / 'shell'
    shutil.copytree(PREFIX / 'upstream/shell', config)
    (config / 'shell.qml').write_text('''import Quickshell
import Quickshell.Io
import "services"
ShellRoot {
  AppLibrary { id: apps }
  IpcHandler {
    target: "probe"
    function list(): string { return JSON.stringify(apps.sortedEntries("")) }
  }
}
''')
    runtime = base / 'runtime'
    runtime.mkdir(mode=0o700)
    env = os.environ | {'HOME': str(home), 'XDG_DATA_HOME': str(home / '.local/share'),
                        'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_RUNTIME_DIR': str(runtime),
                        'XDG_DATA_DIRS': str(base / 'system'), 'XDG_CURRENT_DESKTOP': 'Hyprland',
                        'QT_QPA_PLATFORM': 'offscreen', 'OMARCHY_PATH': str(PREFIX / 'upstream')}
    def ipc(target, method):
        return subprocess.run(['quickshell', '-p', str(config), 'ipc', 'call', target, method],
                              env=env, text=True, capture_output=True, timeout=5)
    def wait_for(predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.1)
        raise AssertionError('Application list did not update within five seconds')
    def names():
        p = ipc('probe', 'list')
        return {row['entry']['id']: row['entry']['name'] for row in json.loads(p.stdout)} if p.returncode == 0 else {}
    def entry(path, name, extra=''):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'[Desktop Entry]\nType=Application\nName={name}\nExec=true\n{extra}')
    log = open('/tmp/omadora-app-refresh.log', 'w')
    process = subprocess.Popen(['quickshell', '-n', '-p', str(config)], env=env, stdout=log, stderr=log)
    try:
        wait_for(lambda: ipc('probe', 'list').returncode == 0)
        # Both directories are created after the shell started: the important
        # first-install case the native watcher can miss.
        local = home / '.local/share/applications/omadora-probe.desktop'
        flatpak = home / '.local/share/flatpak/exports/share/applications/omadora-flatpak.desktop'
        entry(local, 'New local app')
        entry(flatpak, 'New Flatpak app')
        ipc('omadora.apps', 'refresh').check_returncode()
        wait_for(lambda: names().get('omadora-probe') == 'New local app' and 'omadora-flatpak' in names())
        # Updating a file in place need not emit directoryChanged.
        entry(local, 'Renamed app')
        ipc('omadora.apps', 'refresh').check_returncode()
        wait_for(lambda: names().get('omadora-probe') == 'Renamed app')
        # Preserve freedesktop visibility/overrides and remove deleted entries.
        entry(local, 'Hidden app', 'Hidden=true\n')
        flatpak.unlink()
        ipc('omadora.apps', 'refresh').check_returncode()
        wait_for(lambda: 'omadora-probe' not in names() and 'omadora-flatpak' not in names())
        assert process.poll() is None
        print('PASS: live application addition, late Flatpak exports, in-place rename, hidden entry and removal within 5s without shell restart')
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()
