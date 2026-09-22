#!/bin/bash
# Reuse a previously built Fedora system when COPR is temporarily unavailable.
# Run only inside the disposable privileged ISO builder container.
set -euo pipefail
[[ $EUID == 0 && ( -e /run/.containerenv || -e /.dockerenv ) ]]
ref=${1:?Supply the release tag whose desktop will be embedded}
[[ $ref =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]]
test -f /out/payload/omadora-root.tar.xz
# Reusing the payload skips build-root.sh, including its builder dependencies.
dnf install -y git python3 tar xz
(cd /out/payload && sha256sum -c SHA256SUMS)
mkdir -p /build/root
git clone --depth 1 --branch "$ref" https://github.com/DanielCoffey1/omadora.git /build/release-source
release_sha=$(git -C /build/release-source rev-parse HEAD)
echo "Rebasing Fedora payload onto $ref ($release_sha)"
tar --xattrs --acls --selinux --numeric-owner -C /build/root -xJf /out/payload/omadora-root.tar.xz

python3 - "$release_sha" <<'PY'
import json
from pathlib import Path
import shutil
import sys

source = Path('/build/release-source')
root = Path('/build/root')
sys.path.insert(0, str(source))
import omadora as a

prefix = root / 'usr/local/share/omadora'
shutil.rmtree(prefix)
upstream = Path('/build/upstream')
a.fetch_upstream(upstream)
a.assemble(upstream, prefix)
shutil.copy2(source / 'LICENSE', prefix / 'LICENSE')
shutil.copytree(source / 'docs', prefix / 'docs')
for name, destination in (('omadora.desktop', 'usr/share/wayland-sessions/omadora.desktop'),
                          ('omarchy-lock-password', 'etc/pam.d/omarchy-lock-password')):
    shutil.copy2(prefix / 'system' / name, root / destination)
image_path = root / 'etc/omadora/image.json'
image = json.loads(image_path.read_text())
image['version'] = a.VERSION
image['revision'] = sys.argv[1]
image_path.write_text(json.dumps(image, indent=2))
Path('/out/payload/image.json').write_text(json.dumps(image, indent=2))
assert image['offline_wallpapers'] == 332
assert (root / 'usr/local/share/omadora-wallpapers').is_dir()
print('Payload desktop:', image['version'], image['revision'])
PY

chroot /build/root /sbin/setfiles -F -e /proc -e /sys -e /dev -e /run /etc/selinux/targeted/contexts/files/file_contexts /
tar --one-file-system --xattrs --acls --selinux --numeric-owner -C /build/root -c . |
  xz -T0 --memlimit-compress=50% -6 >/out/payload/omadora-root.tar.xz.partial
mv /out/payload/omadora-root.tar.xz.partial /out/payload/omadora-root.tar.xz
(cd /out/payload && sha256sum omadora-root.tar.xz >SHA256SUMS)
echo 'PASS: reused Fedora packages and wallpapers with tagged Omadora desktop.'
