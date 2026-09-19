# Validation record

## Latest verified results

Theme-colored application logos at `159ecb6` pass [55 source checks and the
reproducible font build](https://github.com/DanielCoffey1/omadora/actions/runs/35415234412),
[Fedora integration of the menu changes](https://github.com/DanielCoffey1/omadora/actions/runs/35414868022),
and [all 21 Fedora desktop checks](https://github.com/DanielCoffey1/omadora/actions/runs/35415235518).
The menu now uses 67 bundled monochrome logos for 73 catalog entries, with
matching Install/Remove mappings. Browser, AI, editor and terminal menu
screenshots were reviewed in Tokyo Night and White. The test removed the user
copy of the logo font and restarted Quickshell before opening the menus,
verifying that the runtime FontLoader also works for existing installations.
The original theme was restored. This run uses Fedora Cloud plus the
Workstation package environment, not a new Anaconda ISO installation.

To get this tested revision, log out of Hyprland and run from GNOME or a TTY:

```bash
omadora upgrade --ref 159ecb6e2a668c4f2bd391863642b23a6105ed4a
```

Update/chooser fixes at `4cb2df3` pass [54 source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35406094188),
[Fedora integration of the functional changes](https://github.com/DanielCoffey1/omadora/actions/runs/35406058291),
and [all 20 desktop checks on a fresh Workstation ISO](https://github.com/DanielCoffey1/omadora/actions/runs/35406094638).
The real sudo password prompt appeared in exactly one terminal. The optional
app chooser was visible, cancelled with Escape and closed with Enter; both
screenshots were reviewed. Unit tests verify a bar refresh after successful
and failed DNF transactions, and distinguish failed update queries from an
empty update list. The desktop test cancels at the password prompt; it does
not establish an end-to-end completed DNF upgrade/icon transition.

Dictation's real RPM/model installation and service restart left Super+Return,
workspace switching, floating and close shortcuts working, with no Hyprland
configuration errors. This does not reproduce the reported intermittent
hardware keyboard failure or validate speech transcription. Its service log
did reveal the visualizer failing to load `libgtk4-layer-shell.so.0`;
the follow-up at `b01c5c4` adds Fedora's `gtk4-layer-shell` to the optional RPM
dependencies and adds executable/library checks. Existing Dictation users can
install that package with `sudo dnf install gtk4-layer-shell` and then run
`systemctl --user restart voxtype.service` in their desktop session.
The follow-up passes [source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35407409933)
and [real Fedora RPM installation, visualizer library resolution/help startup,
and removal](https://github.com/DanielCoffey1/omadora/actions/runs/35407409802).
The 20-check desktop result above predates this dependency-only change; the
new visualizer itself has not been visually retested in the desktop VM.

To apply these fixes, log out of Hyprland and run from GNOME or a TTY:

```bash
omadora upgrade --ref b01c5c44ef89e666d1adca12d3d701538988b867
```

The published `v0.1.0-alpha` tag remains unchanged, so plain `omadora upgrade`
does not select these newer fixes yet.

Menu and bar fixes at `5d2f570` pass [50 source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35396591945),
[Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35396592009),
and [all 17 desktop checks on a fresh Workstation ISO installation](https://github.com/DanielCoffey1/omadora/actions/runs/35396591357).
The available-package and installed-package pickers each selected `ripgrep`
and `fzf` through real keyboard input; the probe verified the selected names
without removing those desktop dependencies. The web-app completion terminal
closed with Enter. Recording cancellation, start/stop, three saved WebM files
(silent, desktop audio and microphone), stream inspection and decoding passed.
The reminder panel and timer creation/clear also passed. Menu, picker,
completion and recording screenshots were reviewed; the runtime menu audit
checked 302 entries and 75 executable dependencies. This is VM evidence, not
physical microphone quality, Bluetooth pairing or complete hardware coverage.

The earlier runs exposed missing DNF query separators, retained picker cursor
position and a recorder waiting for screen damage during shutdown. Those were
fixed and retested. The ISO fixture also now waits for GNOME's display
environment before launching Anaconda. These fixes are newer than the
published `v0.1.0-alpha` tag. To install this tested revision, log out of all
Hyprland sessions and run from GNOME or a TTY:

```bash
omadora upgrade --ref 5d2f57031135c5e9bfb30c6412d31a71f9ba5d08
```

Alpha release preparation at `0950e2b` passes [45 source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35370788650)
and [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35370788539).
The bootstrap and updater default to `v0.1.0-alpha`; explicit ref overrides
remain available. Fedora integration initially failed on COPR HTTP 503 package
downloads, then passed on the same revision. See [alpha release notes](releases/v0.1.0-alpha.md).
The owner also reports successful use on a laptop, without hardware details or
individual checklist results; broader hardware coverage remains unverified.

The [fresh Workstation ISO run](https://github.com/DanielCoffey1/omadora/actions/runs/35363116387)
passes at `b76f862`: stock Fedora 44 Anaconda installation, UEFI disk boot with
SELinux enforcing, the public Omadora bootstrap, reboot, and all 15 desktop,
maintenance and recovery checks. See [the ISO record](#fresh-workstation-iso-september-18-2026)
for test instrumentation and boundaries.

The catalog has 93 optional choices, including Codex CLI and Claude Code.
[Both CLI runtime jobs](https://github.com/DanielCoffey1/omadora/actions/runs/35301839112)
pass installation, wrapper version/help, desktop-file validation, removal and
profile preservation; no account or model request was tested. See
[application results](APP_TESTS.md#codex-cli-and-claude-code). The earlier
[complete optional Install mapping](#complete-optional-install-mapping-september-17-2026)
records 38 source tests, 23 automated recipe jobs with passing results across
fixes, and 15 graphical regression checks. Hardware, accounts and interactive
workflows have separate limits.

- At `e7008cd`, [all 29 source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35295603414) and [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35295603480) pass. The expanded 51-entry optional catalog resolves against Fedora, RPM Fusion, Ghostty's community COPR, Sublime's official RPM repository and Flathub. Installed web-app helpers create a valid desktop launcher and remove it successfully. The integration run also repeats installation, configuration, maintenance and recovery checks. New catalog entries were resolved, not installed or launched in this run; the earlier 26-app runtime results do not cover them. See [Install coverage](INSTALL_MENU.md) for mappings and remaining ports.
- At `56d72f7`, [all 25 source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35292980665) and [all 15 graphical checks](https://github.com/DanielCoffey1/omadora/actions/runs/35292980209) pass. The expanded suite uses real keyboard input to exercise window creation, fullscreen/floating toggles, workspace movement and closing; GTK copy/cut/paste and exact-text paste into Foot; and display scaling from 1x to 1.25x and back. Existing desktop, service and recovery checks also pass. This verifies a single virtual display using the default monitor rule, not custom monitor rules, multiple displays or physical hardware.
- At `64be78a`, [all 25 source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35287939908), [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35287939933), and [all 12 graphical checks](https://github.com/DanielCoffey1/omadora/actions/runs/35287939476) pass. The audit records 136 menu entries, 73 command dependencies, 64 predicates and 187 shortcut-help entries. These counts are inventories, not that many fully exercised workflows. The gaming screenshot confirms already-installed GameMode is hidden from Install; its Remove predicate succeeds. Hidden Dell haptic checkmarks return false without invoking the unavailable utility. The [coverage matrix](MENU_AUDIT.md) lists remaining interactive and hardware tests.
- [Twenty-five source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35287260943) and [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35287260935) pass at `0df1acf`, including the menu guard, dependency, shortcut-help and browser-theme-hook fixes. See the [menu audit](MENU_AUDIT.md) for exact coverage and unsupported hardware paths.
- [Twelve graphical checks](https://github.com/DanielCoffey1/omadora/actions/runs/35286572639) pass at `c88d503`: the nine existing checks plus menu dependencies/providers, theme/background/bar controls, and desktop toggle state transitions. Screenshots show populated gaming/font/application menus, Bluetooth's no-adapter state, and fixed-brightness display controls. The battery-only power panel stays hidden in this batteryless VM; its controls are not validated.
- [Twenty-five source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35284969479) pass at `d535a19`, including deployment interruption, repeatable recovery, ownership checks, previous-desktop restoration and verification of saved desktop preferences.
- [Fedora lifecycle integration](https://github.com/DanielCoffey1/omadora/actions/runs/35284969338) passes at `d535a19`: killed install/upgrade recovery, actual no-session-bus preference restoration, published-revision update, rollback, and migration/rollback of the real pre-journal release.
- [Nine graphical checks](https://github.com/DanielCoffey1/omadora/actions/runs/35284733519) pass at `bb606e5`, including GDM login after upgrade and rollback, followed by the eight existing desktop/service/recovery checks.
- [Fifteen source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35280375545) and the [Fedora integration suite](https://github.com/DanielCoffey1/omadora/actions/runs/35280375560) pass at `ed79167`, including the session-activation fix and the minimal-workflow corrections described below.
- [All eight desktop/service/recovery checks](https://github.com/DanielCoffey1/omadora/actions/runs/35281940399) pass at `43261d4`: Activity, screenshot keyboard/clipboard, font preservation, portal selection, network, audio, notifications and GNOME/config recovery.
- GTK dark file chooser styling, sandbox font lookup in three Flatpaks, and restoration of shared GTK/font preferences are verified.
- Native Steam downloads its client and reaches sign-in; Signal and Discord reach their linking/login screens. Install/remove checks pass. No accounts or games were used.
- The GDM/Hyprland startup crash was traced to an inactive login session and fixed; 20 subsequent GDM relaunches across four fresh VMs passed password authentication, including deliberately delayed startup.
- A single Bochs virtual display passed three consecutive S3/resume/password-unlock cycles. This is a [verified VM workaround](VIRTUAL_MACHINES.md), not a virtio driver fix. Default QEMU/virtio S3 still fails; software virtio and pre-sleep display blanking did not provide reliable fixes.

The detailed records below distinguish historical failures, fixes, and remaining limitations. Passing individual checks does not imply every workflow passed.

## Fresh Workstation ISO September 18, 2026

[Run 35363116387](https://github.com/DanielCoffey1/omadora/actions/runs/35363116387),
at `b76f862`, installed the unmodified official
`Fedora-Workstation-Live-44-1.7.x86_64.iso` through its Anaconda Web UI onto a
blank 60 GB virtual disk. The published SHA-256 matched. The installed disk
booted without the ISO, using UEFI, an EFI system partition, ext4 `/boot` and
Btrfs root/home subvolumes. SELinux was enforcing, and the installed kernel
command line omitted the temporary debug-shell and first-boot-service mask.
No Cloud image or DNF Workstation environment installation was used.

The public bootstrap fetched the tested commit and installed Omadora. After
reboot, Hyprland, Quickshell, the menu and animated screensaver started. All
15 acceptance checks passed: desktop upgrade/rollback with password login;
menu dependencies/providers; theme/bar controls; desktop toggles; window and
workspace shortcuts; GTK/Foot clipboard; display scaling; Activity; screenshot
save/copy/cancel; font preference preservation; portal file selection; network
reconnection; virtual audio controls; notifications; and GNOME/config recovery.
The menu audit inventoried 292 entries and 73 command dependencies; these are
not counts of fully exercised workflows. Recovery retained later personal edits.

Anaconda's success screen, desktops after upgrade and rollback, the gaming
menu, dark portal, notification and Omadora wordmark captures were visually
reviewed. Artifacts include installation logs, the package inventory before
Omadora, filesystem baseline, screenshots and `interactions.json`.

The fixture adds an SSH key, a test user/password and sudo access; it creates
the user after Anaconda installation, so GNOME's first-run account wizard is
not covered. Initial Omadora startup uses GDM autologin; maintenance checks
use password login. Storage is unencrypted. Secure Boot, physical GPUs,
multiple monitors, real wireless/audio hardware, suspend/resume and optional
application workloads are not established by this run. Existing virtio S3
limitations remain. See [the fixture documentation](WORKSTATION_ISO.md).

Earlier attempts failed in the fixture before Omadora ran: Fedora 44's KIWI
ISO uses different kernel/initrd paths; serial backpressure stalled boot;
the legacy optical controller did not expose the live media; console setup
competed with test access; and the browser used a newer remote endpoint or
opened before Anaconda's backend was ready. The corrected fixture uses the
ISO's actual paths, continuous serial draining, virtio-SCSI optical media,
separate console access, an SSH tunnel to Fedora 44's local web service and
an explicit backend-readiness check. These were test-harness corrections,
not demonstrated Omadora product defects. Later harness-only diagnostics
publish ISO evidence early and detect critical-error dialogs explicitly.

## Optional Install menu expansion

The original menu replacement incorrectly treated a minimal default installation as a reason to shrink the optional installer menu. The expanded menu restores Editor, Service, nested Development and Style/Font categories, adds browser/terminal/gaming choices, and restores portable Web App, Theme and Background workflows. A Fedora package-name prompt uses DNF's normal confirmation. No optional catalog apps are added to the base profile; `file` and `desktop-file-utils` are explicit utilities for web-app icon validation and launcher maintenance.

The [initial resolution run](https://github.com/DanielCoffey1/omadora/actions/runs/35294995045) rejected unavailable `iosevka-fonts`, `victor-mono-fonts`, `ollama-base`, `scala` and `java-21-openjdk-devel` package names. Java now uses Fedora's `java-devel`; the other entries remain pending verified sources. The [next run](https://github.com/DanielCoffey1/omadora/actions/runs/35295282223) resolved the RPM catalog, including Ghostty's documented COPR, but rejected the unavailable Sublime Flatpak ID. Sublime now uses its official signed stable RPM repository. The final successful run above verifies the corrected mappings. Repository/key configuration remains after optional app removal.

Source checks exercise nested menu hierarchy through the upstream parser, preserve install/remove visibility, reject package-name option injection, and verify that optional repository setup is absent from removal commands. Web-app creation/removal runs the installed shell helpers and validates the resulting desktop file. Graphical interaction with the expanded menu, third-party theme import, new-app launches, toolchain workflows and GPU-backed AI remain outside this run's coverage.

## Window, clipboard and display interaction tests

The [initial expanded run](https://github.com/DanielCoffey1/omadora/actions/runs/35289170609), at `d23129c`, passed 14 of 15 graphical checks. Display scaling failed because the VM fixture appended an explicit monitor rule fixed at 1x, overriding the default rule updated by the scaling helper. The fixture now sets its test resolution through the default rule. This was a test configuration conflict, not a demonstrated defect in the default Omadora configuration.

The [first retry](https://github.com/DanielCoffey1/omadora/actions/runs/35290685867), at `c78c206`, reached the workflow's 30-minute limit while downloading and installing the Workstation environment, before Omadora installation or desktop checks. It provides no scaling result. The fixture now allows ten parallel package downloads and the workflow allows 45 minutes.

The [verified retry](https://github.com/DanielCoffey1/omadora/actions/runs/35292980209), at `56d72f7`, passed all 15 checks. The scaling audit records 1x to 1.25x to 1x, with valid Hyprland configuration and a responsive shell. Window/workspace, GTK clipboard and scaled-display captures were visually inspected. These additions change the test harness and CI configuration; they do not add applications to the minimal product. The VM still uses Fedora Cloud plus the Workstation environment, not an untouched Workstation ISO installation.

## Desktop maintenance and interrupted operations

The [initial lifecycle container run](https://github.com/DanielCoffey1/omadora/actions/runs/35284105182), at `0b805bd`, passed actual SIGKILL interruption during install and upgrade, recovery of the old runtime/configuration/fonts, refusal of invalid user Lua with automatic runtime restoration, successful upgrade, and installed-command rollback. Root snapshots are separate from personal configuration backups. Upgrades and rollback leave personal configuration untouched; initial-install recovery preserves post-install edits in a rescue backup. Tests compare runtime files by SHA-256 and distinguish old/new trees with a fixture marker.

Logs from that initial run also showed that `gsettings` can exit successfully without persisting writes when no user DBus session exists. A stronger test deliberately changes a preference before recovery. The [first run of that stronger check](https://github.com/DanielCoffey1/omadora/actions/runs/35284728161) failed because `dbus-run-session` was missing. The adapter now connects to the existing user bus when available, otherwise starts a temporary session bus, and verifies every restored value. Fedora's `dbus-daemon` package provides that fallback helper and is now explicit in the core dependencies. The first run must not be read as proof of successful offline preference restoration.

The [final container run](https://github.com/DanielCoffey1/omadora/actions/runs/35284969338), at `d535a19`, passed the stronger recovery check: the fixture changed the saved color preference after killing installation, and recovery restored all three original values without a running user bus. It repeated interruption, invalid-config refusal and rollback checks, then exercised the installed `upgrade --ref COMMIT` command fetching the published repository. Fedora's existing broker remained installed; the helper package supplies temporary recovery sessions.

That run also installed the actual old `a009dd3` release in a fresh disposable user, upgraded through the new source checkout, and confirmed that the original configuration-backup reference survived. Invoking the newly installed rollback command restored the legacy runtime byte-for-byte, including removing lifecycle helpers absent from that old version; its original About command worked, and the current source recovery command found no pending transaction. This verifies migration of that particular released layout, not arbitrary modified or pre-journal incomplete installations.

The [graphical maintenance run](https://github.com/DanielCoffey1/omadora/actions/runs/35284733519), at `bb606e5`, passed all nine checks. Starting from a real Omadora session, it switched to GNOME, invoked the installed updater against the published commit, logged back into Omadora and opened Foot. It then switched to GNOME for rollback, logged into Omadora again, and verified that a personal edit survived. Both desktop captures were visually inspected. Activity, screenshot keyboard/clipboard, font preservation, portal file selection, network reconnection, virtual audio, notifications and GNOME/config recovery all passed afterward. This VM had a running user bus; the later explicit `dbus-daemon` dependency and no-bus path were verified by the final container run above. The VM fixture now pins the public bootstrap and repository to the tested commit, preventing later pushes from changing an in-flight test.

Linux source tests additionally interrupt deployment between directory renames and interrupt recovery itself, then repeat recovery; refuse mismatched transaction owners, concurrent operations and incomplete snapshots; and verify that the login entry is withheld until validation. These are process-interruption tests, not storage-corruption or hardware power-loss tests. See [maintenance](MAINTENANCE.md) for the user commands and boundaries.

## Minimal workflow audit

The retained Activity shortcut called an uninstalled monitor, TUI helpers delegated to an unrelated default terminal, and several shortcuts still exposed omitted workflows. Activity now uses `top` in Foot, TUI helpers use Foot, and unsupported menu/shortcut entries are filtered. About customization required omitted Fastfetch tooling and is removed; documentation links now match Omadora and plain Neovim.

Screenshot capture now uses the upstream keyboard picker and supports saving, copying, or both. Linux regression tests exercise saved/clipboard bytes, copy-only cleanup, capture failure, and cancellation with freeze-process cleanup. Font selection previously overwrote a general user Fontconfig file; it now updates only Omadora's managed file. Source tests check both the adapted helper and menu/keybinding consistency.

The [first graphical run](https://github.com/DanielCoffey1/omadora/actions/runs/35280374750) passed seven of eight checks, including Activity in Foot, real font changes with unrelated preferences preserved, portal selection, network, audio, notifications and GNOME/config recovery. Screenshot cancellation passed, but the fullscreen test timed out waiting for SSH. The clipboard owner retains stderr after forking; the fixture now redirects capture output to a guest log so that daemon cannot keep the SSH channel open. This first run is not counted as a complete pass. The dark portal, notification and animated Omadora wordmark captures were visually inspected.

The [corrected graphical run](https://github.com/DanielCoffey1/omadora/actions/runs/35281940399) passed all eight checks at `43261d4`. Escape canceled without creating a file; Ctrl+Enter captured fullscreen, the saved PNG matched the clipboard bytes exactly, and both paths removed their freeze overlays. The actual clipboard image was visually inspected and showed the complete desktop without the selection overlay. Activity opened `top` in Foot and quit normally; changing and restoring the monospace font preserved an unrelated Fontconfig sentinel. Portal, network, virtual audio, notifications and GNOME/config recovery passed again. This fixture correction required no additional product change; [source checks](https://github.com/DanielCoffey1/omadora/actions/runs/35281935436) also passed.

## Session and suspend diagnosis

The [repeated-login baseline](https://github.com/DanielCoffey1/omadora/actions/runs/35252451897) at `bab696e` used Hyprland's packaged desktop entry through UWSM, including `start-hyprland`. Five consecutive GDM restarts passed real wrong-password rejection and correct unlock. S3 still failed: the captured kernel stack placed Hyprland in `drm_atomic_helper_swap_state`, and QEMU displayed "Display output is not active." The host used QEMU 8.2.2 and virglrenderer 1.0.0, with guest Hyprland 0.56.2, Aquamarine 0.15.0 and kernel 7.2.5. This is evidence of a graphics stall, not a failed PAM password check.

The [software-graphics baseline](https://github.com/DanielCoffey1/omadora/actions/runs/35252454364) reproduced the startup crash before any suspend test. Its retained crash report identifies the cause: `Session is not active, waiting for 5s`, followed by `Session could not be activated in time`. Merely using the packaged launcher did not resolve the GDM handoff.

Commit `64f6c42` activates the authenticated local GDM session through logind before starting UWSM, waits for its active state and stops if activation fails. It does not enable autologin or change PAM. [Fourteen source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35254450784), including activation failure and seatless-session behavior, and [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/35254055898) pass.

The [delayed-startup retest](https://github.com/DanielCoffey1/omadora/actions/runs/35254205679) passed with that fix. The disposable fixture deliberately delayed the session launcher by 12 seconds, allowing the GDM greeter to take the active VT before Omadora starts. Initial boot and five consecutive GDM relaunches succeeded; all five relaunches passed two incorrect-password rejections and a correct password unlock. No backend startup crash was recorded. This verifies the repaired handoff in the tested environment, not every display manager or physical GPU.

Two more fresh VMs with the session fix each passed five GDM relaunches and password checks. [Virtio without 3D acceleration](https://github.com/DanielCoffey1/omadora/actions/runs/35254055711) passed the first S3/resume/unlock cycle but failed the second in the same kernel DRM path. [Blanking the display before S3](https://github.com/DanielCoffey1/omadora/actions/runs/35254131881) failed the first cycle. Neither experiment is enabled in the product or counted as a reliable suspend fix. Multiple cycles are required to avoid treating a single successful wake as resolution.

Related upstream evidence: [QEMU issue 2520](https://gitlab.com/qemu-project/qemu/-/issues/2520) describes the same inactive-display symptom after S3. This similarity alone does not prove an identical cause or establish a fix for Omadora.

The [single-Bochs control](https://github.com/DanielCoffey1/omadora/actions/runs/35257282229) passed all eight checks: five GDM relaunches/password checks and three S3/resume/unlock cycles. Kernel logs confirm three actual `deep` sleep entries and exits. The final display capture showed the usable Omadora desktop. No sleep-mode, DPMS, PAM or lock changes were used. This establishes a working alternative VM graphics configuration; it does not establish working virtio S3 or physical-hardware support. The [initial Bochs attempt](https://github.com/DanielCoffey1/omadora/actions/runs/35255719283) inadvertently included QEMU's default VGA as a second GPU, failed rendering before suspend, and is not evidence about Bochs suspend. The corrected fixture explicitly uses `-vga none`.

## Performed in the Windows development workspace

- Twenty-five automated tests, including assembly against the actual pinned Omarchy v4.0.4 tree. Windows runs thirteen and skips twelve Linux/symlink execution cases; Linux CI runs all twenty-five.
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

## Complete optional Install mapping (September 17, 2026)

The catalog now has 91 choices. Every actionable Install entry in the pinned
Omarchy menu has a Fedora mapping, with Firefox and Foot already installed by
the base. No optional catalog applications were added to the base profile.

- [38 source tests](https://github.com/DanielCoffey1/omadora/actions/runs/35298728935)
  pass at `f41b034`, including full upstream Install-action coverage, tampered
  download rejection, archive traversal protection, registration recovery,
  foreign-file preservation and database loopback/credential checks.
- [Fedora integration at d34f1ea](https://github.com/DanielCoffey1/omadora/actions/runs/35297931722)
  resolves every declared catalog RPM/Flatpak and workflow RPM dependency,
  including official vendor repositories and NVIDIA's Flatpak remote. This is
  metadata/transaction resolution, not installation of every native app.
- [The initial 23-job optional matrix](https://github.com/DanielCoffey1/omadora/actions/runs/35297699054)
  passed 17 jobs: Meslo, Victor, Iosevka, Ollama, ONCE binary, ChatGPT, Perplexity,
  Grok Bot, T3 Code, LM Studio, Mise, Cursor, Hermes build, Laravel, Voxtype RPM,
  Hermes source and xpadneo source. Assets were actually downloaded and verified;
  installed payloads/launchers were checked and removed. Source-only jobs verify
  extraction, not application installation. Desktop files and ELF dependencies
  are checked where applicable; graphical app launch is not established.
- [Runtime retries](https://github.com/DanielCoffey1/omadora/actions/runs/35298276691)
  pass Bun, Deno and Phoenix installation, command launch and removal after
  correcting Mise's executable name and the Fedora Erlang dependency. That
  overall run still failed for entries corrected by the runs below.
- [Laravel and Symfony](https://github.com/DanielCoffey1/omadora/actions/runs/35298436578)
  pass actual install, command launch and removal. Symfony's test uses its
  supported `version` subcommand and the installer includes PHP/Composer.
- [OpenClaw](https://github.com/DanielCoffey1/omadora/actions/runs/35298537914)
  passes install, version-command launch and removal with private Node 24.19.0.
  Removal no longer attempts to uninstall a nonexistent gateway service.
  Onboarding, account use and a running systemd gateway remain untested.
- [Scala](https://github.com/DanielCoffey1/omadora/actions/runs/35298729354)
  passes install, Scala/scalac/Scala CLI version commands and removal using
  Fedora's JDK and the required `which` helper.
- [All 15 graphical regression checks](https://github.com/DanielCoffey1/omadora/actions/runs/35297930644)
  pass at `d34f1ea`: 288 menu entries, providers/dependencies, upgrade/rollback
  login, windows/workspaces, GTK/Foot clipboard, scaling, themes, audio, portals,
  notifications and recovery. The gaming menu screenshot was visually checked
  and includes the new entries. These are desktop regressions, not 288 fully
  exercised workflows. Later optional-runtime fixes were tested separately.

All 23 selected noninteractive matrix recipes therefore have passing results
across the recorded runs; this is not a claim that all 91 choices have undergone
fresh end-to-end installation and workload testing. New native vendor apps have
resolution evidence only. Windows guest creation, ONCE service workloads,
rootless database workloads, Bluetooth/xpadneo/Secure Boot, microphone/model
inference, game installation/play and account login remain unvalidated. The VM
uses Fedora Cloud plus Workstation packages, not an untouched Workstation ISO.

The first matrix exposed and fixed actual dependency/runtime defects. Historical
red runs are retained as evidence rather than relabeled successful. See
[Install mapping details](INSTALL_MENU.md) for removal/data-retention behavior.
