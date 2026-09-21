#!/bin/bash
# Run only in the disposable privileged Fedora container used by iso.yml.
set -euo pipefail
[[ $EUID == 0 && -e /run/.containerenv || $EUID == 0 && -e /.dockerenv ]]
[[ ! -e /build/root ]] || { echo 'Use a fresh build container.' >&2; exit 1; }
mkdir -p /build /out
exec > >(tee /out/build-root.log) 2>&1
dnf install -y dnf5-plugins python3 git curl lorax xorriso isomd5sum xz cpio dosfstools mtools pykickstart
ksvalidator -v F44 /src/iso/installer.ks.in
git config --global --add safe.directory /src
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
chroot /build/root /sbin/setfiles -F -e /proc -e /sys -e /dev -e /run /etc/selinux/targeted/contexts/files/file_contexts /
cleanup
for point in dev proc sys run; do
  if mountpoint -q "/build/root/$point"; then
    echo "Build mount remains active: $point" >&2
    exit 1
  fi
done
trap - EXIT
find /build/root/var/cache -mindepth 1 -delete
find /build/root/var/log -type f -exec truncate -s 0 {} +
rm -f /build/root/var/lib/systemd/random-seed /build/root/etc/ssh/ssh_host_* /build/root/root/.bash_history
