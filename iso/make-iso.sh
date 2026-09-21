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
base=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/iso
image=Fedora-Everything-netinst-x86_64-44-1.7.iso
curl -fL --connect-timeout 20 --max-time 600 --retry 2 "$base/$image" -o /build/fedora-boot.iso
curl -fL --connect-timeout 20 --max-time 600 --retry 2 "$base/Fedora-Everything-44-1.7-x86_64-CHECKSUM" -o /out/fedora-CHECKSUM
expected=$(sed -n "s/^SHA256 ($image) = //p" /out/fedora-CHECKSUM)
[[ $expected =~ ^[0-9a-f]{64}$ ]]
printf '%s  /build/fedora-boot.iso\n' "$expected" | sha256sum -c -
mkdir -p /build/updates/etc/anaconda/profile.d
cp /src/iso/omadora.conf /build/updates/etc/anaconda/profile.d/
printf '[Main]\nProduct=Omadora\nVersion=44\nIsFinal=False\n' >/build/updates/.buildstamp
mkdir -p /build/images
(cd /build/updates && find . -print0 | cpio --null -o -H newc | gzip -9) >/build/images/updates.img
# Auto-load customization from the already mounted installation media. An
# explicit inst.updates=LABEL path can select the overlapping USB partition
# after Anaconda has mounted the whole ISO device, which Linux refuses to open.
mkksiso --ks /build/omadora.ks --add /out/payload/omadora-root.tar.xz --add /build/images \
  --volid OMADORA_44 --cmdline 'inst.graphical inst.webui inst.profile=omadora' \
  --replace 'Fedora 44' 'Omadora' \
  /build/fedora-boot.iso /out/Omadora-44-x86_64.iso
xorriso -indev /out/Omadora-44-x86_64.iso -ls /images
(cd /out && sha256sum Omadora-44-x86_64.iso >SHA256SUMS)
ls -lh /out/Omadora-44-x86_64.iso
mkdir -p /out/test
# Only this unshipped copy enables serial debug access for the disposable VM.
mkksiso --cmdline 'console=ttyS0,115200 systemd.debug_shell=ttyS0 inst.sshd' \
  /out/Omadora-44-x86_64.iso /out/test/omadora-test.iso
echo 'PASS: built offline Omadora installer ISO.'
