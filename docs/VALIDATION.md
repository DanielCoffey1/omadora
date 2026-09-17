# Validation record

## Latest verified results

- Thirteen source tests and the Fedora integration suite pass at `0eeeebd`.
- GTK dark file chooser styling, sandbox font lookup in three Flatpaks, and restoration of shared GTK/font preferences are verified.
- Native Steam downloads its client and reaches sign-in; Signal and Discord reach their linking/login screens. Install/remove checks pass. No accounts or games were used.
- Default QEMU/virtio S3 resume/unlock still fails. The s2idle diagnostic did not establish a working alternative. One intermittent GDM/Hyprland backend startup crash is also recorded.

The detailed records below distinguish historical failures, fixes, and remaining limitations. Passing individual checks does not imply every workflow passed.

## Performed in the Windows development workspace

- Thirteen automated tests, including assembly against the actual pinned Omarchy v4.0.4 tree. Windows runs twelve and skips the real-symlink case when symlink creation is not permitted; Linux CI runs that case.
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

This container does not boot systemd, GDM or a GPU; PAM file creation is not proof of password unlock.

## Booted Fedora VM result

[Run 35191812108](https://github.com/DanielCoffey1/omadora/actions/runs/35191812108), at commit `727b9a2`, passed on September 17, 2026:

- Checksum-verified official Fedora Cloud 44 image with the full Workstation environment installed, under QEMU/KVM with software-rendered virtio graphics.
- Actual Omadora installation, followed by a reboot and GDM autologin into the Omadora session.
- UWSM, Hyprland and the Quickshell desktop started; the running compositor reported no configuration errors.
- Shell IPC responded; the desktop, menu and animated screensaver were captured. The menu visibly showed **About Omadora** and the bar rendered icon glyphs.
- The power-profile adapter queried the running TuneD service and listed its profiles.
- SELinux remained **Enforcing**.

The initial screenshot resolution was 640×480. A second [passing run at 1920×1080](https://github.com/DanielCoffey1/omadora/actions/runs/35192513285), at commit `80a0142`, confirmed the complete menu and centered animated **OMADORA** wordmark. Desktop, menu and screensaver screenshots were visually inspected. This is not a complete pixel-by-pixel comparison with upstream or a multi-monitor test.

The first VM attempt reached the shell but hit its default two-second IPC timeout immediately after startup; the fixture now waits for startup to settle and permits ten seconds for IPC on software-rendered graphics. This timeout change applies only to the test.

This fixture installs Workstation onto Fedora Cloud; it is not a test of an untouched Workstation ISO installation. The initial autologin smoke test did not validate password authentication, profile changes, device behavior, portals or app transactions; the extended results below cover additional paths. Logs also contain system-service/SELinux warnings and Hyprland's recommendation to use start-hyprland; a passing smoke test does not establish a warning-free session.

## Extended acceptance testing

The first [extended run](https://github.com/DanielCoffey1/omadora/actions/runs/35228793702) verified two rejected passwords followed by a successful password unlock, compositor lock retention after rejection, terminal/workspace/window shortcuts, and Catppuccin/Tokyo Night theme switching. The run as a whole failed: clipboard output handling, SSH-session polkit authorization, suspend, and app transactions required further investigation. Individual passes must not be read as a passing overall run.

The [service/recovery run](https://github.com/DanielCoffey1/omadora/actions/runs/35230137074) verified actual file selection through the portal, network reconnection, notifications, and a GNOME session with configuration restoration and rescue of post-install edits. Its audio operations succeeded, but the panel assertion expected text from a void IPC method; that assertion was corrected for the rerun.

The corrected [service/recovery suite](https://github.com/DanielCoffey1/omadora/actions/runs/35231577423) passed all five checks, including the real Audio menu action and volume/mute controls on the emulated HDA output. The audio panel screenshot was inspected. This run also exercised the published `curl .../boot.sh | bash` installation command. Virtual controls do not establish physical sound quality, microphone routing or Bluetooth audio behavior.

The [second interaction run](https://github.com/DanielCoffey1/omadora/actions/runs/35230375200) passed authentication, keyboard/windows, clipboard, all three power-profile changes and restoration of the original profile, and theme switching. **Default-configuration suspend/resume failed.** Fedora entered ACPI S3 and resumed, but the compositor did not accept the unlock afterward. On termination, the captured stack showed Aquamarine blocked in `drmModeAtomicCommit`; restarting GDM did not recover the display. This is a failed end-to-end suspend test on QEMU/virtio graphics, not proof of working suspend on physical hardware. The app suite was moved before suspend to avoid contaminating its independent results.

An isolated [legacy-DRM diagnostic](https://github.com/DanielCoffey1/omadora/actions/runs/35233118781) repeated the same five interaction passes and the post-resume unlock failure with `AQ_NO_ATOMIC=1` in the fixture's UWSM environment. It is not a validated workaround and is not enabled by Omadora. Upstream documents the variable in [Aquamarine's environment settings](https://github.com/hyprwm/aquamarine/blob/main/docs/env.md); it was used only to investigate the failing virtual graphics path.

The [maintenance/container run](https://github.com/DanielCoffey1/omadora/actions/runs/35231692616) passed cancellation of a native app install, refusal to overwrite an existing installation, a real Fedora update transaction with byte-for-byte retention of pinned desktop files, and the empty user Flatpak update path. It also repeated the installer/configuration checks and catalog resolution. This does not exercise a Flatpak application version upgrade or an OS release upgrade.

Defects found in the additional audit: Setup → Audio referenced a removed helper, and Setup → Network relied on an absent `nmtui` binary; both now use the current shell panels. Node.js used generic package capabilities instead of Fedora's installed RPM names; the catalog now names `nodejs22` and `nodejs22-npm`, so presence checks and removal address the actual packages.

The app harness now uses a pseudo-terminal to answer each real package prompt. Buffered input had been consumed by the first of multiple DNF calls, and Flatpak rejected the noninteractive prompt. The cloud VM also needed Fedora's kernel metapackage to supply its emulated audio driver. These are fixture corrections, separate from the product fixes.

Visual discrepancy observed: the GTK file chooser uses Fedora's light styling while the shell uses Tokyo Night. Full GTK/application theme parity is still incomplete. GameMode's functional self-test also failed its CPU-governor check in the VM; a binary/version smoke test is not proof of working performance tuning on real hardware.

The [full catalog run](https://github.com/DanielCoffey1/omadora/actions/runs/35234023393) completed all 26 install commands and all 23 attempted removals. Three entries were already present and retained. Launch review found a missing Lutris display dependency, an incorrect Chromium test command, and several preliminary dialogs that must not count as complete application launches. See the [per-application results](APP_TESTS.md), including the Signal wrapper warning and sandbox font warning. The later suspend/unlock test failed again; the five preceding interaction checks passed.

After the Network menu and Lutris dependency corrections, [source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35237020761) and the [Fedora integration/maintenance suite](https://github.com/DanielCoffey1/omadora/actions/runs/35237020707) passed at commit `eb6b7fa`. The [focused graphical retest](https://github.com/DanielCoffey1/omadora/actions/runs/35237031270) then confirmed the Network panel action and Lutris, Chromium and GIMP interfaces. Discord progressed beyond its updater but its capture still showed loading; Steam failed to create a main window within five minutes, with assertion dumps logged. All five selected app installations/removals passed. The five ordinary interaction checks passed again, while post-suspend unlocking failed again. See the application report for the reviewed results and limits.

## Theme, font and recovery corrections

The [theme/font integration run](https://github.com/DanielCoffey1/omadora/actions/runs/35242901364), at `e95ca23`, passed. The adapter now retains the upstream GTK preference helper (previously blocked because a comment mentioned an Arch-only command), includes the Yaru icons it selects, and uses standard user fontconfig configuration instead of exporting a host-only `FONTCONFIG_FILE` into sandboxes.

The [recovery retest](https://github.com/DanielCoffey1/omadora/actions/runs/35242932206) passed all five service checks and verified restoration of the original GTK color scheme, theme and icon settings, removal of the managed font preference when originally absent, and rescue of later configuration edits. The session reported the expected Nerd Font and dark preference. However, screenshot review still found a light GTK file chooser, so preference-setting success does not establish complete GTK visual integration.

The [s2idle diagnostic](https://github.com/DanielCoffey1/omadora/actions/runs/35243940410) passed authentication, window controls, clipboard, power profiles and dark/light/dark GTK preference switching. Its suspend attempt failed: SSH did not recover after the RTC wake deadline, and the kernel journal could not be retrieved to confirm sleep entry/exit. This does not validate s2idle or isolate the root cause of the earlier S3 failure. No sleep-mode override is installed by Omadora. An earlier diagnostic failed before boot because QEMU's display was not ready; the fixture now waits for Xvfb to accept clients.

The [four-app retest](https://github.com/DanielCoffey1/omadora/actions/runs/35242929475) passed all four installs/removals and font lookup inside Signal, Discord and Bottles without the former host-path fontconfig error. Discord reached its login form and Bottles rendered its welcome interface in dark styling. Steam still failed; its newly collected client log identified inability to load trusted root certificates and download its update manifest. The test accidentally selected No at Signal's wrapper, so that result does not demonstrate an application crash. The five ordinary interaction checks passed; S3 post-resume unlocking failed again.

A [GTK diagnostic run](https://github.com/DanielCoffey1/omadora/actions/runs/35244347989) failed before reaching its portal checks: Hyprland aborted during startup with `CBackend::create() failed` while GDM's greeter also used the virtual GPU. This is a separate intermittent startup failure; the successful earlier startup runs do not erase it. Subsequent fixtures collect Hyprland crash reports as well as the journal.

At `80be428`, [Linux source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35246575514) passed all thirteen tests, including rejection of a replaced configuration-parent symlink before any restoration and preservation of edited Steam desktop entries. The [Fedora integration suite](https://github.com/DanielCoffey1/omadora/actions/runs/35246575513) also passed. The new Steam wrapper uses the current Fedora CA bundle only in Steam's process environment; the optional desktop entry routes all RPM-provided actions through it. Toolkit environment variables now reach UWSM before portal services are activated.

The [service retest at that commit](https://github.com/DanielCoffey1/omadora/actions/runs/35246577948) passed all five checks, including GNOME restoration after the new environment setup. Its diagnostics confirmed a native Wayland portal window and `Adwaita-dark` in both GTK and the settings portal, while the screenshot remained light. The profile lacked the separate Adwaita-dark theme entry supplied by upstream's `gnome-themes-extra` dependency. Omadora now provides a small entry that imports GTK's own bundled dark CSS. A resolved GTK background-color check was added to catch this class of mismatch.

The [final theme/recovery run](https://github.com/DanielCoffey1/omadora/actions/runs/35248151319), at `2e4a544`, passed all five service checks. GTK resolved the window background to RGB `(0.208, 0.208, 0.208)`, and the portal screenshot was visually reviewed: the file chooser now renders dark. GTK settings and the managed font preference restored correctly in GNOME, with later edits rescued. The [source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35248151711) and [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35248151808) also passed. This resolves the observed light file chooser; it is not a full visual-parity certification for every application.

The [final native Steam retest](https://github.com/DanielCoffey1/omadora/actions/runs/35249426231), at `0eeeebd`, passed installation, actual client download, sign-in-window rendering and removal after adding the legacy certificate-path link. The ineffective environment wrapper from `80be428` was removed. Authentication, keyboard/windows, clipboard, power profiles and theme switching passed again. The new rendered GTK checks measured dark backgrounds near RGB `(0.208, 0.208, 0.208)` and light near `(0.965, 0.961, 0.957)`. **The workflow still failed at S3 post-resume unlocking.** [Source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35249426900) and [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35249426932) passed separately at the same commit.

## Manual and hardware acceptance procedure

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
