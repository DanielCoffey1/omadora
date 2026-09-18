# Fresh Workstation ISO acceptance test

The `Fresh Workstation ISO` workflow starts from Fedora's official
`Fedora-Workstation-Live-44-1.7.x86_64.iso`, verifies its published SHA-256,
and attaches a blank 60 GB virtual disk. It uses UEFI firmware and the stock
Anaconda Web UI. It does not convert a Fedora Cloud image or install the
Workstation environment through DNF.

The ISO is unchanged. Boot-only automation enables a serial debug shell and
masks the live environment's console first-boot service to avoid competing
terminal readers. An SSH tunnel exposes Fedora 44's existing local installer
web service only on host loopback. The fixture uses a disposable SSH key, a
test account/password and a sudo rule. No physical host disk is
attached. The test uses unencrypted guest storage and does not establish Secure
Boot compatibility. After installation, `python3-pexpect` supplies acceptance
test instrumentation; Fedora supplies the desktop and kernel.

The installed guest must identify as Workstation, boot in UEFI mode and have
SELinux enforcing. Omadora's public `boot.sh` is then fetched at the workflow
commit, with `OMADORA_REF` set to the same commit. Pinning the test revision
prevents a concurrent push from changing the installer under test.

After installing Omadora and rebooting, the fixture runs the existing desktop,
upgrade/rollback login and GNOME/config recovery suite. Initial Omadora startup
uses test-only GDM autologin; the lifecycle checks exercise password login.
This is automated validation in virtual hardware, not a manual installation on
a physical computer or proof of every GPU, wireless device or app workload.

Artifacts include the ISO checksum and file inventory, Anaconda screenshots and
logs, the installed package inventory before Omadora, baseline OS/filesystem
details, and the later desktop acceptance results. Inspect the result and
artifacts of a completed run before treating the workflow as passing evidence.

Run from GitHub Actions, or with:

```bash
gh workflow run workstation-iso.yml --repo DanielCoffey1/omadora
```

The older `Fedora recovery and services` workflow remains a separate Cloud-plus-
Workstation-packages regression fixture. Its previous passing results do not
substitute for this ISO test.
