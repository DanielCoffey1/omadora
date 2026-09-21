#!/bin/bash
set -euo pipefail
test -f /build/root/etc/omadora/image.json
for point in dev proc sys run; do
  if mountpoint -q "/build/root/$point"; then exit 1; fi
done
mkdir -p /out/payload
exec > >(tee /out/pack.log) 2>&1
du -sh /build/root
tar --one-file-system --xattrs --acls --selinux --numeric-owner -C /build/root -c . |
  xz -T0 --memlimit-compress=50% -6 >/out/payload/omadora-root.tar.xz.partial
mv /out/payload/omadora-root.tar.xz.partial /out/payload/omadora-root.tar.xz
cp /out/image.json /out/packages.txt /out/payload/
(cd /out/payload && sha256sum omadora-root.tar.xz >SHA256SUMS)
ls -lh /out/payload/omadora-root.tar.xz
