"""Assemble a pristine offline image inside a disposable Fedora build container."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import urlopen

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
import omadora as a

root = Path(sys.argv[1]).resolve()
assert root == Path('/build/root'), 'Only the disposable build root is supported'
prefix = root / 'usr/local/share/omadora'
upstream = Path('/build/upstream')
a.fetch_upstream(upstream)
a.assemble(upstream, prefix)
for name in ('omadora', 'omadora-session'):
    path = root / 'usr/local/bin' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to('/usr/local/share/omadora/bin/' + name)
for source, target in [('omadora.desktop', 'usr/share/wayland-sessions/omadora.desktop'),
                       ('omarchy-lock-password', 'etc/pam.d/omarchy-lock-password')]:
    dest = root / target
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prefix / 'system' / source, dest)

# The ISO includes every original so changing wallpaper never requires networking.
catalog = json.loads((prefix / 'assets/wallpapers/catalog.json').read_text())
originals = prefix / 'assets/wallpapers/originals'
originals.mkdir()
def download(row):
    with urlopen(catalog['base_url'] + row['asset'], timeout=90) as response:
        data = response.read(row['size'] + 1)
    assert len(data) == row['size'] and hashlib.sha256(data).hexdigest() == row['sha256'], row['name']
    (originals / row['id']).write_bytes(data)
with ThreadPoolExecutor(max_workers=6) as pool:
    list(pool.map(download, catalog['images']))

image = {'name': 'Omadora', 'version': a.VERSION, 'revision': a.lifecycle().revision(SOURCE),
         'fedora': 44, 'architecture': 'x86_64', 'offline_wallpapers': len(catalog['images'])}
a.write(root / 'etc/omadora/image.json', json.dumps(image, indent=2))
a.write(root / 'etc/hostname', 'omadora\n')
a.write(root / 'etc/machine-id', '')
a.write(root / 'etc/fstab', '# Configured by the Omadora installer.\n')
a.write(root / 'etc/locale.conf', 'LANG=en_US.UTF-8\n')
a.write(root / 'etc/vconsole.conf', 'KEYMAP=us\n')
a.write(root / 'etc/dracut.conf.d/omadora-image.conf', 'hostonly="no"\n')
a.write(root / 'etc/gdm/custom.conf', '[daemon]\nDefaultSession=omadora.desktop\n')
# Keep Fedora identity for DNF and adapter preflight; distinguish the remix visibly.
osrelease = root / 'usr/lib/os-release'
text = osrelease.read_text()
text = '\n'.join('PRETTY_NAME="Omadora (Fedora 44)"' if line.startswith('PRETTY_NAME=') else line for line in text.splitlines()) + '\n'
osrelease.write_text(text)
subprocess.run(['chroot', str(root), 'usermod', '--lock', 'root'], check=True)
subprocess.run(['chroot', str(root), 'authselect', 'select', 'local', '--force'], check=True)
subprocess.run(['systemctl', '--root', str(root), 'enable', 'gdm', 'NetworkManager', 'firewalld', 'chronyd'], check=True)
subprocess.run(['systemctl', '--root', str(root), 'set-default', 'graphical.target'], check=True)
subprocess.run(['chroot', str(root), 'rpm', '-qa', '--qf', '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n'], check=True,
               stdout=Path('/out/packages.txt').open('w'))
Path('/out/image.json').write_text(json.dumps(image, indent=2))
print('PASS: image runtime assembled; all wallpaper originals verified.', flush=True)
