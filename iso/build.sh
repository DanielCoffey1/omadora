#!/bin/bash
# Run only in the disposable privileged Fedora container used by iso.yml.
set -euo pipefail
[[ $EUID == 0 && -e /run/.containerenv || $EUID == 0 && -e /.dockerenv ]]
[[ ! -e /build/root ]] || { echo 'Use a fresh build container.' >&2; exit 1; }
mkdir -p /build /out
exec > >(tee /out/build.log) 2>&1
dnf install -y dnf5-plugins python3 git curl lorax xorriso isomd5sum xz cpio dosfstools mtools
dnf copr enable -y nett00n/hyprland
dnf copr enable -y whelanh/omarchy
mapfile -t packages < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' /src/packages/core.txt /src/iso/packages.txt)
dnf --installroot=/build/root --releasever=44 --use-host-config --setopt=install_weak_deps=False install -y "${packages[@]}"
mkdir -p /build/root/{dev,proc,sys,run}
mount --rbind /dev /build/root/dev
mount --make-rslave /build/root/dev
mount -t proc proc /build/root/proc
mount --rbind /sys /build/root/sys
mount --make-rslave /build/root/sys
mount -t tmpfs tmpfs /build/root/run
cleanup() { umount -R /build/root/run /build/root/sys /build/root/proc /build/root/dev 2>/dev/null || true; }
trap cleanup EXIT
python3 /src/iso/prepare.py /build/root
cp /etc/yum.repos.d/*copr* /build/root/etc/yum.repos.d/
for directory in /build/root/usr/lib/modules/*; do
  version=${directory##*/}
  chroot /build/root dracut --force --no-hostonly "/boot/initramfs-$version.img" "$version"
done
chroot /build/root /sbin/setfiles -F -e /proc -e /sys -e /dev -e /run -r / /etc/selinux/targeted/contexts/files/file_contexts /
cleanup
trap - EXIT
find /build/root/var/cache -mindepth 1 -delete
find /build/root/var/log -type f -exec truncate -s 0 {} +
rm -f /build/root/var/lib/systemd/random-seed /build/root/etc/ssh/ssh_host_* /build/root/root/.bash_history
tar --xattrs --acls --selinux --numeric-owner -C /build/root -c . | xz -T2 -6 > /build/omadora-root.tar.xz
payload_sha=$(sha256sum /build/omadora-root.tar.xz | cut -d' ' -f1)
sed "s/@PAYLOAD_SHA256@/$payload_sha/" /src/iso/installer.ks.in >/build/omadora.ks
ksvalidator -v F44 /build/omadora.ks
base=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/iso
image=Fedora-Everything-netinst-x86_64-44-1.7.iso
curl -fL --retry 3 "$base/$image" -o /build/fedora-boot.iso
curl -fL --retry 3 "$base/Fedora-Everything-44-1.7-x86_64-CHECKSUM" -o /out/fedora-CHECKSUM
expected=$(sed -n "s/^SHA256 ($image) = //p" /out/fedora-CHECKSUM)
[[ $expected =~ ^[0-9a-f]{64}$ ]]
printf '%s  /build/fedora-boot.iso\n' "$expected" | sha256sum -c -
mkdir -p /build/updates/etc/anaconda/profile.d
cp /src/iso/omadora.conf /build/updates/etc/anaconda/profile.d/
(cd /build/updates && find . -print0 | cpio --null -o -H newc | gzip -9) >/build/updates.img
mkksiso --ks /build/omadora.ks --add /build/omadora-root.tar.xz --updates /build/updates.img \
  --volid OMADORA_44 --cmdline 'inst.graphical inst.webui inst.profile=omadora' \
  --replace 'Install Fedora' 'Install Omadora' \
  /build/fedora-boot.iso /out/Omadora-44-x86_64.iso
(cd /out && sha256sum Omadora-44-x86_64.iso >SHA256SUMS)
ls -lh /out/Omadora-44-x86_64.iso
mkdir -p /out/test
# Only this unshipped copy enables serial debug access for the disposable VM.
mkksiso --cmdline 'console=ttyS0,115200 systemd.debug_shell=ttyS0 inst.sshd' \
  /out/Omadora-44-x86_64.iso /out/test/omadora-test.iso
echo 'PASS: built offline Omadora installer ISO.'
