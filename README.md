# Omadora

**Omarchy 4's desktop, a minimal app selection, and Fedora underneath.**

Independent project at [DanielCoffey1/omadora](https://github.com/DanielCoffey1/omadora). Targets fresh **Fedora Workstation 44, x86_64**. Upstream desktop pinned to Omarchy **v4.0.4**, commit `c668141e9c42b13c80c9ca4ea108e11708c5e8a5`.

**Development build, not a validated release.** The adapter and generated tree have automated tests. Installation, RPM resolution, GDM login, graphics, PAM unlocking, suspend and visual parity still need a Fedora VM. Do not describe this as a finished 1:1 port yet. See [validation](docs/VALIDATION.md) and [compatibility](docs/COMPATIBILITY.md).

## Install

Development installer (Fedora VM testing is still required):

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/main/boot.sh | bash
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

After installation, log out, select **Omadora** using GDM's gear menu, and log in. GNOME remains available. Fedora's existing apps are retained; Omadora doesn't remove Workstation packages.

## What you get

- Upstream Hyprland layout, Quickshell bar, menus, notifications, lock screen and theme system.
- Omadora text branding and an Omadora ASCII wordmark using the existing animated screensaver engine.
- Foot terminal, Neovim, Firefox and Files, plus desktop infrastructure for networking, sound, brightness, clipboard and screenshots.
- Omarchy's additional app and web-app shortcuts disabled; essential desktop shortcuts remain.
- Optional software in **Install**, grouped by Gaming, Creative, Media, Productivity, Communication, Development, Terminal and Browser. Matching Remove menus.
- Configuration backups before setup and a restore command that preserves later edits in a second backup.

No games, office suite, media editor, music client, AI agent, container engine or proprietary chat app is installed by Omadora's base profile. Fedora Workstation's own existing applications are left in place.

## Optional apps

| Menu selection | Installation source |
| --- | --- |
| Gaming → Steam | Native RPM via RPM Fusion |
| Gaming → Lutris, MangoHud, GameMode | Fedora RPMs |
| Gaming → Heroic, Bottles, RetroArch, ProtonUp-Qt | User-scoped Flathub |
| Creative → GIMP | Fedora RPM |
| Creative → OBS Studio, Kdenlive | User-scoped Flathub |
| Productivity → LibreOffice | Fedora RPM |
| Productivity → Obsidian, Bitwarden | User-scoped Flathub |
| Development → Podman, Node.js, Go, Rust | Fedora RPMs |
| Development → Visual Studio Code | User-scoped Flathub; sandboxed distribution |

Full catalog: [apps.json](apps.json). Package-manager prompts remain visible in a terminal. Selecting one app installs that app and its dependencies; selecting a category does not install a bundle. RPM Fusion is enabled only when Steam is requested. Flathub is added to the user's Flatpak configuration only when a Flatpak app is requested. The catalog manages its user-scoped Flatpaks; system-wide installations are outside its removal scope.

```bash
omadora app list
omadora app install steam --dry-run
omadora app install heroic
omadora app remove heroic
```

## Repositories and maintenance

Desktop dependencies come from Fedora and the community `nett00n/hyprland` COPR. `ttfx`, required for the upstream animated screensaver, comes from the community `whelanh/omarchy` COPR. These are external maintainers, not Fedora or Omadora's own package repositories. Enabling them can affect later DNF transactions. Missing or incompatible packages stop installation; the installer never uses `--skip-broken` or disables signature checks.

The desktop source is pinned; RPM versions remain controlled by the configured repositories. This is not yet a reproducible package release. A maintained, versioned Omadora RPM repository is a release requirement.

```bash
omadora update                  # Fedora package upgrades
flatpak update --user           # Optional Flatpak updates
omadora doctor                 # Basic executable diagnostics
```

Desktop upgrades and system rollback are not implemented in this alpha. Re-running install refuses to overwrite an existing Omadora installation. Fedora's kernel, bootloader, firewalld, SELinux and GNOME display manager remain under Fedora's management. Do not run Omarchy's upstream installation or migration scripts on Fedora.

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

The source checkout passed to `build` should be the pinned release. `install` fetches the tag and verifies the exact commit before building. The build output includes `portability-report.json`, listing upstream system commands replaced with explicit unsupported-operation messages. These are incomplete porting work, not silent successes. The GitHub workflow checks Python tests, shell syntax and bootstrap ShellCheck; it does not boot Fedora.

## Credits

Omadora's adapter is MIT licensed. Omarchy's desktop is by its upstream contributors and remains MIT licensed, with its unmodified license retained in the generated tree. Nerd Fonts / JetBrains Mono font attribution is in [assets/fonts](assets/fonts). Internal `omarchy-*` command names, paths, IPC IDs and plugin authorship remain for compatibility and attribution; visible product text and screensaver branding use Omadora.

This is independent of both upstream Omarchy and the existing `elpritchos/omadora` project. See [third-party sources](docs/THIRD_PARTY.md).
