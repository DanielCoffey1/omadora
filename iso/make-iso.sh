#!/bin/bash
set -euo pipefail
mkdir -p /build /out
exec > >(tee /out/make-iso.log) 2>&1
dnf install -y lorax pykickstart curl git xorriso isomd5sum cpio dosfstools mtools
git config --global --add safe.directory /src
(cd /out/payload && sha256sum -c SHA256SUMS)
cp /out/payload/image.json /out/payload/packages.txt /out/
git -C /src rev-parse HEAD >/out/installer-revision.txt
payload_sha=$(sha256sum /out/payload/omadora-root.tar.xz | cut -d' ' -f1)
sed "s/@PAYLOAD_SHA256@/$payload_sha/" /src/iso/installer.ks.in >/build/omadora.ks
ksvalidator -v F44 /build/omadora.ks
(cd /out/installer-base && sha256sum -c SHA256SUMS)
cp /out/installer-base/SHA256SUMS /out/installer-base-SHA256SUMS.txt
mkdir -p /build/updates/etc/anaconda/profile.d
cp /src/iso/omadora.conf /build/updates/etc/anaconda/profile.d/
printf '[Main]\nProduct=Omadora\nVersion=44\nIsFinal=False\n' >/build/updates/.buildstamp
mkdir -p /build/images
(cd /build/updates && find . -print0 | cpio --null -o -H newc | gzip -9) >/build/images/updates.img
# Auto-load customization from the already mounted installation media. An
# explicit inst.updates=LABEL path can select the overlapping USB partition
# after Anaconda has mounted the whole ISO device, which Linux refuses to open.
mkksiso --ks /build/omadora.ks --add /out/payload/omadora-root.tar.xz --add /build/images \
  --volid OMADORA_44 --cmdline 'inst.graphical inst.profile=omadora' \
  --replace 'Omadora 44' 'Omadora' \
  /out/installer-base/boot.iso /out/Omadora-44-x86_64.iso
xorriso -indev /out/Omadora-44-x86_64.iso -ls /images
(cd /out && sha256sum Omadora-44-x86_64.iso >SHA256SUMS)
ls -lh /out/Omadora-44-x86_64.iso
mkdir -p /out/test
# Only this unshipped copy enables serial debug access for the disposable VM.
# Keep the graphical console primary so installer services do not share
# their main console with the test debug shell.
mkksiso --cmdline 'console=ttyS0,115200 console=tty0 systemd.debug_shell=ttyS0 inst.sshd' \
  /out/Omadora-44-x86_64.iso /out/test/omadora-test.iso
echo 'PASS: built offline Omadora installer ISO.'
