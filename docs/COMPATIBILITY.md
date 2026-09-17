# Compatibility and deliberate differences

## Implemented in the adapter

- Pinned Omarchy 4.0.4 source verification and staged desktop assembly.
- Minimal package manifest; no upstream application provisioning, app launchers, AI setup, Arch installation or migrations.
- Generated Fedora Install/Remove menus for 26 explicitly mapped optional apps.
- User-visible Omadora branding; original wordmark replaced, including the default screensaver and branding reset target. Upstream author/license attribution and technical names remain.
- DNF package updates and RPM presence queries; cached DNF update checks for the bar.
- Separate GDM entry, UWSM session environment, Fedora PAM includes and the upstream shell's polkit authentication agent.
- Configuration backup and restore with preservation of post-install edits.

## Differences from upstream

- Firefox is the default browser; web links open as normal Firefox windows rather than Chromium app-mode windows.
- Screenshots use grim/slurp and copy to the clipboard; the annotation editor and advanced capture tools are not installed.
- Omarchy's optional app shortcuts and AI status widget are disabled in the minimal profile.
- Gaming/other apps use Fedora RPMs, RPM Fusion or user-scoped Flatpak. No AUR or Arch package-name passthrough.
- Fedora's GDM, bootloader, kernel, networking, SELinux and firewalld remain in charge.
- Arch setup, installation, package, refresh and update commands without a Fedora implementation fail explicitly. Their menu entries are filtered out; some advanced workflows are intentionally unavailable.
- Optional app coverage is the explicit catalog, not every Omarchy installer. Xbox controller DKMS setup, Battle.net automation, proprietary vendor repositories and language-version managers still need individual Fedora ports.

## Release blockers

1. Keep testing the core manifest against Fedora 44 and the selected COPRs. The first real installer, native Hyprland config and Quickshell import run passed on September 17, 2026; graphical behavior and future package combinations still need validation.
2. Resolve the reproduced QEMU/virtio suspend/resume hang. A [single Bochs display](VIRTUAL_MACHINES.md) provides a verified VM workaround with three passing S3/resume/unlock cycles; the virtio driver issue remains. The GDM/Hyprland startup crash was traced to an inactive login session and fixed; 20 repeated logins passed across four VMs, including deliberately delayed launches. Expand the passing desktop/password/recovery checks to an untouched Workstation ISO installation and physical GPUs. Complete application theme parity and multi-monitor testing remain. The existing fixture uses Workstation packages on the official Fedora Cloud image; it exercises GDM autologin and actual lock-screen password authentication with SELinux enforcing.
3. Audit every retained menu and keybinding for transitive calls to blocked or uninstalled commands. Text scanning is a conservative first pass, not a complete dependency analysis.
4. Finish the remaining application launch checks and exercise Flatpak launcher discovery, account/gameplay workflows, real Flatpak version upgrades and offline/error cases. All 26 catalog install commands and 23 attempted removals passed the full run; see [application results](APP_TESTS.md) for failures and limits. The sandbox font fix passed in Signal, Discord and Bottles; expand that retest to the remaining Flatpaks.
5. Implement versioned Omadora packages, desktop upgrades, partial-install recovery/uninstallation and reproducible RPM sources. Current user-config restore is not an OS rollback.
6. Run hardware tests for Intel/AMD; develop a separate NVIDIA driver/Secure Boot path before claiming NVIDIA support.

Silverblue/Kinoite, Fedora spins, Fedora versions other than 44, ARM/Asahi, and existing customized desktops are outside this initial target. GNOME is preserved as a fallback, but applying shared home-directory configuration can still affect tools launched from GNOME.
