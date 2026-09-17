"""Upgrade and roll back the actual pre-journal release in the disposable container.

Run as root only in the container fixture, after all ordinary lifecycle checks.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

assert os.geteuid() == 0 and Path('/.dockerenv').exists(), 'Disposable Docker container only'
source = Path(__file__).resolve().parents[1]
prefix = Path('/usr/local/share/omadora')


def run(*args):
    subprocess.run([str(a) for a in args], check=True, timeout=900)


def user(*args):
    run('sudo', '-iu', 'omadora-legacy', *args)


def hashes():
    return {str(p.relative_to(prefix)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in prefix.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


# Reset only the system paths owned by this disposable test deployment.
for path in (prefix, Path('/var/lib/omadora'), Path('/usr/local/bin/omadora'),
             Path('/usr/local/bin/omadora-session'), Path('/etc/pam.d/omarchy-lock-password'),
             Path('/usr/share/wayland-sessions/omadora.desktop')):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)
run('useradd', '--create-home', 'omadora-legacy')
sudoers = Path('/etc/sudoers.d/omadora-legacy')
sudoers.write_text('omadora-legacy ALL=(ALL) NOPASSWD: ALL\n')
sudoers.chmod(0o440)
legacy = Path('/home/omadora-legacy/source')
user('git', 'init', legacy)
user('git', '-C', legacy, 'remote', 'add', 'origin', 'https://github.com/DanielCoffey1/omadora.git')
user('git', '-C', legacy, 'fetch', '--depth', '1', 'origin', 'a009dd30fdfb5ced82ada6957975e2d45740f09f')
user('git', '-C', legacy, 'checkout', '--detach', 'FETCH_HEAD')
user('python3', legacy / 'omadora.py', 'install')
assert not (prefix / 'omadora_deploy.py').exists()
before = hashes()
metadata = Path('/home/omadora-legacy/.local/state/omadora/installation.json')
original_backup = json.loads(metadata.read_text())['backup']
user('python3', source / 'omadora.py', 'upgrade', '--local')
assert (prefix / 'omadora_deploy.py').exists()
assert json.loads(metadata.read_text())['backup'] == original_backup
user('/usr/local/bin/omadora', 'rollback')
assert hashes() == before, 'Legacy runtime was not restored exactly'
user('/usr/local/bin/omadora', 'about')
user('python3', source / 'omadora.py', 'recover')
Path('/results/omadora-legacy.json').write_text(json.dumps([
    'PASS: installed actual a009dd3 release, upgraded through the new checkout, retained original config backup',
    'PASS: installed rollback command restored legacy runtime byte-for-byte, including removal of lifecycle helpers; no pending transaction'
], indent=2))
