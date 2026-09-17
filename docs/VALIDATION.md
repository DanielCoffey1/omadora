# Validation record

## Performed in the Windows development workspace

- Ten automated tests, including assembly against the actual pinned Omarchy v4.0.4 tree.
- Fedora/edition/architecture rejection rules.
- Optional-app command construction and catalog input constraints.
- Arch menu replacement and absence of direct Arch package-manager calls in generated command files.
- User-config backup/restore, preservation of later edits, malformed-manifest rejection and incomplete-backup rejection before deletion.
- Omadora screensaver wordmark, display-name replacement, internal environment-name preservation and upstream license preservation.
- Bundled font SHA-256 and license presence.

These are implementation tests, not evidence of a bootable or visually matching Fedora desktop.

## Fedora 44 integration result

[Run 35190472661](https://github.com/DanielCoffey1/omadora/actions/runs/35190472661), at commit `1611178`, passed:

- Real installation in a Fedora 44 container with Workstation identity and preinstalled TuneD.
- The complete core RPM transaction, including Hyprland 0.56.2, Quickshell 0.3.1, and ttfx 0.3.2.
- Configuration backup, root-owned runtime deployment, user configuration and Tokyo Night theme generation, GDM session-file creation, and PAM configuration-file creation.
- `Hyprland --verify-config` returned `config ok`.
- All 13 native Quickshell modules used by the desktop loaded in an offscreen smoke test.
- TuneD remained installed, without adding the conflicting power-profiles-daemon service.
- The combined optional native RPM transaction resolved; it was canceled before installing apps. All Flatpak application IDs were found in Flathub's app listing. This verifies availability/resolution, not each app's runtime behavior.

Defects fixed during testing: incorrect `polkit-gnome`/`libvips-tools` package names, duplicate external polkit agent, Hyprland version probing without XDG_RUNTIME_DIR, and the conflicting power-management daemon. Container fixture identity and Quickshell smoke-test shutdown behavior were also corrected.

This container does not boot systemd, GDM or a GPU; PAM file creation is not proof of password unlock, and the power-profile adapter still needs a running service test.

## Fedora VM acceptance procedure

Use a disposable Fedora Workstation 44 x86_64 VM and take a hypervisor snapshot before installation. Record package versions, GPU model, compositor version and the Omadora source commit.

1. Run the dry-run plan. Confirm no optional applications are in the base transaction.
2. Run installation and save the complete terminal log. A missing core RPM is a failure to fix, not an item to skip.
3. Reboot; verify both GNOME and Omadora appear in GDM. Log into each.
4. Check `journalctl --user -b`, `omadora doctor`, and `hyprctl configerrors` for startup failures.
5. Compare screenshots against Omarchy 4.0.4 for bar geometry, theme colors, terminal, menu, notifications, screensaver and lock screen. Check Omadora wording and every icon glyph.
6. Test Super+Return, Super+Space, workspaces, moving/resizing windows, clipboard, sound, brightness, notifications, screenshot capture and theme/background switching.
7. Invoke screensaver manually; check wordmark, animation, per-monitor coverage and input dismissal. Test timed locking, password unlock, repeated wrong passwords, suspend/resume and lid behavior with SELinux enforcing.
8. Test a portal file picker and browser screen sharing, network reconnection and Bluetooth pairing.
9. Install/remove Steam, Lutris and Heroic through the menus. Verify Fedora/RPM Fusion/Flatpak transactions and gamepad discovery. Verify canceling a package prompt does not report success.
10. Test a DNF upgrade, Flatpak upgrade and desktop version retention. No Arch package manager should be invoked.
11. Restore the original config from GNOME. Confirm pre-install content is restored and newer edits remain in the rescue backup.
12. Repeat with interrupted network, insufficient disk space, a preexisting config symlink, failed dependency resolution and an interrupted installation. Complete partial-install recovery before release.

The Adapter checks workflow covers source checks. The [first published run](https://github.com/DanielCoffey1/omadora/actions/runs/35189367740) passed all ten tests, bootstrap Bash syntax and ShellCheck, and syntax validation of the generated Bash scripts. Separate Fedora container and graphical VM workflows exercise installation and the running desktop; their results must be assessed independently.
