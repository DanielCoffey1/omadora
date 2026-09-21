"""Exercise real image first-login setup and idempotence for a second Fedora user."""
import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile

assert os.getuid() == 0
subprocess.run(['useradd', '--create-home', 'omadora-image-test'], check=True)
user = pwd.getpwnam('omadora-image-test')
home = Path(user.pw_dir)
marker = Path('/etc/omadora/image.json')
assert not marker.exists()
marker.parent.mkdir(exist_ok=True)
marker.write_text(json.dumps({'name': 'Omadora', 'fixture': 'first-login-component-test'}))
try:
    with tempfile.TemporaryDirectory(prefix='omadora-image-runtime-') as tmp:
        os.chown(tmp, user.pw_uid, user.pw_gid)
        command = ['sudo', '-iu', user.pw_name, 'env', 'XDG_RUNTIME_DIR=' + tmp,
                   'dbus-run-session', '--', 'python3', '/usr/local/share/omadora/omadora_image.py']
        subprocess.run(command, check=True)
        complete = home / '.local/state/omadora/image-user.json'
        assert complete.is_file()
        assert (home / '.local/state/omarchy/current/background').resolve().name == 'Nepal_5160x2160.png'
        for parent in (home / '.config', home / '.local'):
            assert all(path.lstat().st_uid == user.pw_uid for path in parent.rglob('*'))
        bindings = home / '.config/hypr/bindings.lua'
        before = bindings.read_text() + '\n-- user edit survives subsequent login\n'
        bindings.write_text(before)
        # The root test writer deliberately restores the user's ownership.
        os.chown(bindings, user.pw_uid, user.pw_gid)
        first = complete.read_text()
        subprocess.run(command, check=True)
        assert bindings.read_text() == before
        assert complete.read_text() == first
    print('PASS: new image user gets Nepal/config/fonts/toolkit palette; second login preserves personal edits.')
finally:
    marker.unlink()
