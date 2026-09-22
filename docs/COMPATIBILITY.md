# Compatibility and deliberate differences

## Implemented in the adapter

- Pinned Omarchy 4.0.4 source verification and staged desktop assembly.
- Minimal package manifest; no upstream application provisioning, app launchers, AI setup, Arch installation or migrations.
- Generated Fedora Install/Remove menus for 93 optional choices, including Codex CLI and Claude Code. See [the full mapping](INSTALL_MENU.md).
- User-visible Omadora branding; original wordmark replaced, including the default screensaver and branding reset target. Upstream author/license attribution and technical names remain.
- The bar menu button uses a Fedora glyph from Omadora's Nerd Font and inherits the bar's theme color.
- The default bar clock uses 12-hour time with AM/PM.
- New terminal windows opened by Omadora's terminal shortcut start in the user's home directory.
- DNF package updates and RPM presence queries; cached DNF update checks for the bar.
- Separate GDM entry, UWSM session environment, Fedora PAM includes and the upstream shell's polkit authentication agent.
- Configuration backup and restore with preservation of post-install edits.
- Journaled desktop upgrades, interrupted-operation recovery and a previous-desktop rollback command. Maintenance runs from GNOME or a TTY and preserves personal configuration; see [maintenance](MAINTENANCE.md).

- Hardware-aware graphics setup: matched AMD/Intel libraries, optional multilib gaming support, verified NVIDIA current/580xx selection, Secure Boot gating, and per-process GPU offload. See [graphics](GRAPHICS.md) for limitations.

## Differences from upstream

- Firefox is the initial default browser; web apps open in the current default browser as normal browser windows rather than Chromium app-mode windows.
- Theme changes do not install machine-wide browser color policies. Chromium toolbar-color synchronization and Apple vendor HID brightness controls are not ported.
- Screenshots retain the upstream keyboard region picker, including Escape cancellation and Ctrl+Enter for fullscreen, with grim/slurp capture and save/copy modes. The annotation editor, OCR and QR capture tools are not installed.
- The recording indicator opens region/full-display recording and stops an active recording. Fedora's `wf-recorder` saves VP8 WebM files to the Videos folder, with optional desktop or microphone audio. Encoding uses the CPU; simultaneous audio mixing, webcam overlays and upstream GPU encoder options are not implemented.
- Activity opens the installed `top` monitor in Foot. TUI launchers use Foot directly. Shortcuts for omitted agents, sharing, transcoding and the upstream recording/reminder bindings are removed. Recording and reminders are available through the menu and bar.
- The Dictation indicator opens optional Dictation installation when `voxtype` is absent, then its configuration once installed. Dictation remains outside the minimal base. The Updates indicator opens one terminal and lets Enter close it after completion.
- About uses Omadora's text information; Fastfetch styling entries are omitted. Documentation links point to Omadora and the installed plain Neovim.
- Font selection updates the managed `fontconfig/conf.d/99-omadora.conf` file and preserves unrelated `fontconfig/fonts.conf` preferences.
- Omarchy's optional app shortcuts and AI status widget are disabled in the minimal profile.
- The shortcut help omits browser-extension actions that are not installed. Menu package predicates use Fedora helpers, including the shell's embedded guard path. See the [menu audit](MENU_AUDIT.md).
- Gaming/other apps use Fedora RPMs, RPM Fusion or user-scoped Flatpak. No AUR or Arch package-name passthrough.
- Fedora's GDM, bootloader, kernel, networking, SELinux and firewalld remain in charge.
- Arch setup, installation, package, refresh and update commands without a Fedora implementation fail explicitly. Their menu entries are filtered out; some advanced workflows are intentionally unavailable.
- The pinned upstream Install actions have Fedora mappings. Xbox controller DKMS setup, Battle.net/Lutris setup, vendor repositories and language/framework installers are implemented, but their evidence varies: source checks, package resolution, installation/removal, and actual workloads are recorded separately in [application results](APP_TESTS.md). Mapping a menu entry does not prove complete upstream parity.

## Release blockers

1. Keep testing the core manifest against Fedora 44 and the selected COPRs. The first real installer, native Hyprland config and Quickshell import run passed on September 17, 2026; graphical behavior and future package combinations still need validation.
2. Resolve the reproduced QEMU/virtio suspend/resume hang. A [single Bochs display](VIRTUAL_MACHINES.md) provides a verified VM workaround with three passing S3/resume/unlock cycles; the virtio driver issue remains. The GDM/Hyprland startup crash was traced to an inactive login session and fixed; 20 repeated logins passed across four VMs, including deliberately delayed launches. The [fresh Workstation ISO test](WORKSTATION_ISO.md) now passes installation, UEFI disk boot and all 15 desktop/maintenance/recovery checks with SELinux enforcing. Physical GPU, full application theme parity and multi-monitor testing remain. The older Cloud-plus-Workstation fixture remains separate; neither fixture establishes physical hardware support.
3. Expand the [menu and shortcut audit](MENU_AUDIT.md) to every interactive combination and physical hardware path. Embedded Arch guards and missing desktop utility dependencies found during the audit are fixed; dependency checks, source inspection and false hardware predicates do not establish complete functional coverage.
4. Finish the remaining application launch checks and exercise Flatpak launcher discovery, account/gameplay workflows, real Flatpak version upgrades and offline/error cases. The original 26 catalog install commands and 23 attempted removals passed their run. Additional automated optional-recipe jobs, including Codex CLI and Claude Code, now pass; these are not end-to-end workload checks of all 93 choices. See [application results](APP_TESTS.md) for scopes and limits. The sandbox font fix passed in Signal, Discord and Bottles; expand that retest to the remaining Flatpaks.
5. Implement signed/versioned Omadora packages, uninstallation and reproducible RPM sources. Journaled desktop upgrades and recovery are implemented, but do not merge incompatible user-config migrations, undo RPM transactions, or recover pre-journal partial installations. Desktop/config restoration is not an OS rollback.
6. Run the [physical hardware checklist](HARDWARE_TESTING.md) for Intel/AMD; validate the new [GPU setup and Secure Boot flow](GRAPHICS.md) on physical NVIDIA hardware before claiming hardware support. The read-only inventory collector prepares evidence but does not establish a hardware pass.

Silverblue/Kinoite, Fedora spins, Fedora versions other than 44, ARM/Asahi, and existing customized desktops are outside this initial target. GNOME is preserved as a fallback, but applying shared home-directory configuration can still affect tools launched from GNOME.
