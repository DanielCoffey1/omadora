#!/bin/bash
# Compose the modern Anaconda wizard; Fedora's stock netinst ISO has only GTK UI.
set -euo pipefail
mkdir -p /build /out/installer-base
exec > >(tee /out/build-installer.log) 2>&1
dnf install -y lorax squashfs-tools
lorax --product Omadora --version 44 --release 44 --variant workstation \
  --installpkgs anaconda-webui --volid OMADORA_44 --rootfs-type squashfs \
  --source https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/ \
  --source https://download.fedoraproject.org/pub/fedora/linux/updates/44/Everything/x86_64/ \
  --workdir /build/lorax-work --logfile /out/lorax.log /build/installer
unsquashfs -ll /build/installer/images/install.img >/out/installer-files.txt
grep -q 'usr/share/cockpit/anaconda-webui' /out/installer-files.txt
cp /build/installer/images/boot.iso /out/installer-base/boot.iso
cp /out/installer-files.txt /out/installer-base/
(cd /out/installer-base && sha256sum boot.iso >SHA256SUMS)
echo 'PASS: installer runtime includes the Anaconda Web UI.'
