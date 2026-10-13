# Omadora

**Omarchy 4's desktop, a minimal app selection, and Fedora underneath.**

Independent project at [DanielCoffey1/omadora](https://github.com/DanielCoffey1/omadora). Targets fresh **Fedora Workstation or KDE Plasma Desktop 44, x86_64 (non-Atomic)**. KDE installation is enabled; a full KDE/SDDM hardware smoke test remains pending. Upstream desktop pinned to Omarchy **v4.0.4**, commit `c668141e9c42b13c80c9ca4ea108e11708c5e8a5`.

**v0.5.0-alpha.** [Release notes](docs/releases/v0.5.0-alpha.md) · [Quick start](docs/QUICKSTART.md). Fedora tests cover installation, the original 26 catalog install commands, 23 attempted app removals, GDM/desktop startup, password unlocking, window controls, clipboard, themes, power profiles, portals, audio controls, updates, and GNOME/configuration recovery. Steam startup, GTK dark dialogs and the GDM inactive-session startup crash are fixed and verified; Signal and Discord reached their linking/login screens. **Suspend/resume passed three cycles with a [Bochs virtual display](docs/VIRTUAL_MACHINES.md); QEMU/virtio still fails.** A laptop smoke test was reported by the project owner; detailed hardware results, broader application workloads and complete visual parity remain unvalidated. This is not a finished 1:1 port yet. See [validation](docs/VALIDATION.md), [application results](docs/APP_TESTS.md), and [compatibility](docs/COMPATIBILITY.md).

## Install

### Test KDE and manual NVIDIA setup on a new PC

Start with a fresh **Fedora KDE Plasma Desktop or Workstation 44, x86_64
(non-Atomic)** installation. Open a terminal and paste this command as your
normal user:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/fix/kde-manual-nvidia/boot.sh | OMADORA_REF=fix/kde-manual-nvidia bash
```

This installs the test branch from [PR #1](https://github.com/DanielCoffey1/omadora/pull/1),
including KDE support and manual NVIDIA driver management. Internet access is
required. Enter your sudo password when prompted and save the configuration
backup path printed by the installer.

After installation, install NVIDIA drivers yourself if needed, then reboot.
Select **Omadora** in the KDE login screen's session menu (Plasma Login Manager
on Fedora 44, or SDDM where configured) or GDM's gear menu (Workstation)
and log in. Your existing Plasma or GNOME desktop remains available.

If Omadora is already installed, log out of Omadora, enter Plasma/GNOME or a
TTY, and use this command instead:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/fix/kde-manual-nvidia/boot.sh | OMADORA_REF=fix/kde-manual-nvidia bash -s -- upgrade
```

### Fedora KDE package conflict

If installation stops with files from `kf6-kmime` conflicting with an installed
`kmime` package, Fedora's older KMime package needs to be replaced with its
renamed counterpart. Run:

```bash
sudo dnf swap --refresh kmime kf6-kmime
```

Review the transaction before accepting. If it proposes removing Plasma or many
unrelated applications, cancel and inspect the proposed changes. After a
successful swap, rerun the fresh-install command above. This conflict happens
before Omadora deploys its desktop configuration; the installer does not
force package removal or overwrite conflicting RPM files.

If signing out of Plasma produces a black screen before the login screen,
press **Ctrl+Alt+F3** (some laptops also require **Fn**) and log into the text
console. Collect the login-manager status and current boot logs before rebooting:

```bash
systemctl status display-manager --no-pager -l
sudo journalctl -b -u display-manager -u plasmalogin -u sddm -u gdm --no-pager -n 100
```

An immediate black screen before choosing Omadora does not establish an
Omadora session failure. The installation can update existing Plasma/Qt
packages while resolving desktop dependencies. Save the logs and reboot once
to test the login screen with those updates loaded.

### Other installation options

The **offline ISO** provides a graphical wizard: choose your disk and account,
install, then reboot into Omadora. It includes pywal16 and all 332 wallpapers,
with Nepal selected automatically. [USB guide and verified build](docs/ISO.md).
Offline UEFI installation and first login passed in a VM; hardware testing and
a permanent public ISO download host remain open.

The [fresh Fedora Workstation ISO acceptance test](docs/WORKSTATION_ISO.md)
passes installation, reboot and all 15 desktop/update/rollback/recovery checks
in a UEFI VM with SELinux enforcing. Physical hardware validation remains open.
The [hardware test kit](docs/HARDWARE_TESTING.md) collects a read-only baseline
and provides the local GPU/display/network/suspend checklist.

Install the latest development version from `main` on **Fedora Workstation 44,
x86_64 (non-Atomic)**:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/main/boot.sh | OMADORA_REF=main bash
```

This includes changes made after v0.5.0-alpha, including default-browser web
apps, a 12-hour bar clock and terminals starting in your home directory. `main`
changes as updates are pushed; it is not a tagged release. `OMADORA_REF=main`
selects the latest source because the bootstrap otherwise fetches v0.5.0-alpha.

The KDE and manual NVIDIA changes are available on `fix/kde-manual-nvidia`
using the test command above until PR #1 is merged;
the pinned v0.5.0-alpha release still requires Workstation and retains its old
optional NVIDIA setup.

To install the pinned **v0.5.0-alpha release** instead:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.5.0-alpha/boot.sh | bash
```

Run as your regular user. The installer uses sudo for packages and system files.

Inspect the plan without changing anything:

```bash
python3 omadora.py install --dry-run
```

Install from a local checkout on Fedora:

```bash
python3 omadora.py install
```

After installation, log out and select **Omadora** using GDM's gear menu (Workstation) or the KDE login screen's session selector (Plasma Login Manager on Fedora 44, or SDDM where configured). Your existing GNOME or Plasma desktop and Fedora apps remain available. Omadora does not replace the login manager.

NVIDIA drivers are managed manually after installation. Omadora does not install proprietary NVIDIA drivers, build NVIDIA modules, rebuild the initramfs for them, or enroll Secure Boot keys. Existing drivers are left in place. See [graphics setup](docs/GRAPHICS.md).

## What you get

- Upstream Hyprland layout, Quickshell bar, menus, notifications, lock screen and theme system.
- Omadora text branding and an Omadora ASCII wordmark using the existing animated screensaver engine.
- Foot terminal, Neovim, Firefox and Files, plus desktop infrastructure for networking, sound, brightness, clipboard and screenshots.
- Web apps open in standalone windows without browser tabs, using native Brave when installed or the included Chromium. The bar clock uses 12-hour time with AM/PM, and the terminal shortcut opens in your home directory.
- Activity opens `top` in Foot. Screenshot selection supports Escape to cancel and Ctrl+Enter for fullscreen, saving and copying the image without an extra editor.
- Omarchy's additional app and web-app shortcuts disabled; essential desktop shortcuts remain.
- Optional software in **Install**, including AI, Gaming, Editor, Browser, Terminal, Services, Development and Style → Font, plus creative/media/productivity apps. Matching Remove menus. Web App installation and wallpaper-based color generation are also available; see [Install coverage](docs/INSTALL_MENU.md).
- Configuration backups before setup and a restore command that preserves later edits in a second backup.

No games, office suite, media editor, music client, AI agent, container engine or proprietary chat app is installed by Omadora's base profile. Fedora Workstation's own existing applications are left in place.

Theme switching also sets the user's GTK light/dark preference, GTK theme and icon theme. The monospace font preference uses a managed user fontconfig file; changing it preserves unrelated Fontconfig preferences. These user-wide settings can affect GNOME and other applications; their original values are backed up for configuration recovery.

## Wallpapers

Choose **Style → Wallpapers & colors** to browse the supplied collection and
generate matching pywal16 colors. Fresh installs use Nepal_5160x2160.png. Add
wallpapers under **Install → Style**, and remove them under **Remove**.
See [wallpaper behavior and color coverage](docs/WALLPAPERS.md).

## Optional apps

| Menu selection | Installation source |
| --- | --- |
| Gaming → Steam | Native RPM via RPM Fusion |
| Gaming → Lutris, MangoHud, GameMode | Fedora RPMs |
| Gaming → Heroic, Bottles, RetroArch, ProtonUp-Qt | User-scoped Flathub |
| Creative → GIMP | Fedora RPM |
| Creative → OBS Studio, Kdenlive | User-scoped Flathub |
| Productivity → LibreOffice | Fedora RPM |
| Productivity → Obsidian; Services → Bitwarden, Signal, Spotify, Dropbox | User-scoped Flathub |
| Development → Podman, JavaScript → Node.js, Go, Rust and additional language tools | Fedora RPMs |
| Editor → Visual Studio Code, Zed | User-scoped Flathub; sandboxed distribution |
| Editor → Sublime Text | Official signed vendor RPM repository |
| Terminal → Ghostty | Community `scottames/ghostty` COPR |

The expanded catalog contains 93 entries. Full catalog: [apps.json](apps.json); [upstream mappings and workflow differences](docs/INSTALL_MENU.md). Package-manager prompts remain visible in a terminal. Selecting one app installs that app and its dependencies; selecting a category does not install a bundle. RPM Fusion is enabled only when Steam is requested. Ghostty enables the community `scottames/ghostty` COPR only when selected; its repository remains configured after removal. Sublime Text adds its official stable RPM repository and signing key only when selected; these remain after removing the app. Flathub is added to the user's Flatpak configuration only when a Flatpak app is requested. The catalog manages its user-scoped Flatpaks; system-wide installations are outside its removal scope.

Managed downloads, developer frameworks, Windows virtualization, controller setup and database containers are also available on request. Downloads are checksum-verified, and removal retains personal data. Optional apps replaces the upstream Preinstalls bundle with an explicit picker. See [Install coverage](docs/INSTALL_MENU.md) for sources, updates and workflow limits.

Installing native Steam also adds `/etc/pki/tls/cert.pem` as a compatibility link to Fedora's maintained CA bundle if that legacy path is absent. Existing trust configuration is preserved and TLS verification stays enabled. This shared compatibility link remains after app removal, like the RPM Fusion repository configuration; Steam uses its original RPM-provided desktop launcher.

```bash
omadora app list
omadora app install steam --dry-run
omadora app install heroic
omadora app remove heroic
```

## Repositories and maintenance

Desktop dependencies come from Fedora and the community `nett00n/hyprland` COPR. `ttfx`, required for the upstream animated screensaver, comes from the community `whelanh/omarchy` COPR. These are external maintainers, not Fedora or Omadora's own package repositories. Enabling them can affect later DNF transactions. Missing or incompatible packages stop installation; the installer never uses `--skip-broken` or disables signature checks.

Omadora source defaults to `v0.5.0-alpha`; Omarchy source is pinned separately. Plain `omadora upgrade` stays on this alpha; choose a future published tag with `--ref`. RPM versions remain controlled by the configured repositories. The [alpha Fedora integration run](https://github.com/DanielCoffey1/omadora/actions/runs/35370788539) resolved and installed the core manifest successfully. This is not yet a reproducible package release. A maintained, versioned Omadora RPM repository is a stable-release requirement.

```bash
omadora update                  # Fedora package upgrades
omadora upgrade --ref v0.5.0-alpha # Omadora desktop release; run from GNOME or a TTY
omadora rollback                # Previous desktop; run from GNOME or a TTY
omadora recover                 # Complete recovery of an interrupted operation
flatpak update --user           # Optional Flatpak updates
omadora doctor                 # Basic executable diagnostics
```

Desktop maintenance requires logging out of all Hyprland sessions. Upgrades fetch this repository, assemble the pinned upstream desktop, install required RPM dependencies, snapshot the existing desktop, and validate your Hyprland configuration before completing the change. Personal configuration, selected theme and font are preserved; new user-config defaults are not automatically merged. One previous desktop is kept for `omadora rollback`. See [maintenance and recovery](docs/MAINTENANCE.md).

Older installations that do not recognize `upgrade` can use the bootstrap from GNOME or a TTY:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.5.0-alpha/boot.sh | bash -s -- upgrade
```

Re-running `install` still refuses to overwrite an existing deployment. Desktop recovery/rollback does not undo RPM transactions, enabled repositories, or Fedora upgrades. Fedora's kernel, bootloader, firewalld, SELinux and GNOME display manager remain under Fedora's management. Do not run Omarchy's upstream installation or migration scripts on Fedora.

## Recover configuration

Log into GNOME or a TTY, then use the backup path printed during installation:

```bash
omadora restore-config ~/.local/state/omadora/backups/TIMESTAMP
```

This restores the managed user configuration and saves edits made since install into another backup. It does **not** undo DNF transactions, remove repository definitions, or uninstall Omadora. If installation fails after system staging, the backup path is also recorded in `~/.local/state/omadora/installation.json`; use `python3 /usr/local/share/omadora/omadora.py restore-config PATH` if the command link was not created.

## Develop

```bash
python3 -m unittest discover -s tests -v
git clone --branch v4.0.4 --depth 1 https://github.com/omacom/omarchy.git /tmp/omarchy
OMADORA_TEST_UPSTREAM=/tmp/omarchy python3 -m unittest discover -s tests -v
python3 omadora.py build --source /tmp/omarchy --output build/stage
```

The source checkout passed to `build` should be the pinned release. `install` fetches the tag and verifies the exact commit before building. The build output includes `portability-report.json`, listing upstream system commands replaced with explicit unsupported-operation messages. These are incomplete porting work, not silent successes. GitHub workflows cover source checks, Fedora container installation and a manually dispatched booted graphical VM. See the validation record for exact coverage and limitations.

## Credits

Omadora's adapter is MIT licensed. Omarchy's desktop is by its upstream contributors and remains MIT licensed, with its unmodified license retained in the generated tree. Nerd Fonts / JetBrains Mono font attribution is in [assets/fonts](assets/fonts). Internal `omarchy-*` command names, paths, IPC IDs and plugin authorship remain for compatibility and attribution; visible product text and screensaver branding use Omadora.

This is independent of both upstream Omarchy and the existing `elpritchos/omadora` project. See [third-party sources](docs/THIRD_PARTY.md).
