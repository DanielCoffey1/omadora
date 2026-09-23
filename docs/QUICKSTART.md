# Omadora v0.5.0-alpha quick start

Target: fresh Fedora Workstation **44, x86_64**, non-Atomic. This is an alpha
release of the minimal Omarchy 4.0.4 desktop port. GNOME and Fedora's existing
apps remain available. See [known limits](releases/v0.5.0-alpha.md).

## Install

For the latest development version from `main`, run from a terminal as your
regular Fedora user:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/main/boot.sh | OMADORA_REF=main bash
```

This includes changes after v0.5.0-alpha: web apps follow the default browser,
the bar clock uses 12-hour time with AM/PM, and the terminal shortcut opens in
your home directory. `main` changes as updates are pushed; it is not a tagged
release.

For the pinned **v0.5.0-alpha release**, use:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.5.0-alpha/boot.sh | bash
```

The bootstrap defaults to fetching `v0.5.0-alpha`; the latest-development
command explicitly selects `main` with `OMADORA_REF=main`.
The installer requests sudo for packages/system files, enables the
documented desktop COPRs and backs up managed user configuration. Save the
backup path it prints. Internet access is required.

After installation, log out. Select your user in GDM, choose **Omadora** in
the gear menu, and log in. Check the version with `omadora about`. Use the
desktop's **Install** menu for optional apps, including Gaming and AI.

## Wallpapers

Fresh installations use Nepal_5160x2160.png and pywal16 colors. Open **Style →
Wallpapers & colors** to browse and apply another wallpaper. Use **Install →
Style → Add wallpapers** or **Remove → Remove wallpapers** to manage the library.
See [wallpaper color coverage](WALLPAPERS.md).

## Graphics and gaming

Fresh installs ensure AMD/Intel Mesa and firmware packages for detected hardware.
For NVIDIA, remain in GNOME and run `omadora gpu setup --nvidia --gaming` before
starting Omadora. Secure Boot enrollment may require a reboot and rerunning setup.
**Setup → Graphics** provides status and optional gaming-library setup. See
[GPU setup, supported branches and hybrid laptops](GRAPHICS.md).

## Update

Fedora packages: `omadora update`. Optional user Flatpaks: `flatpak update --user`.

For Omadora itself, log out of all Hyprland sessions and enter GNOME or a TTY:

```bash
omadora upgrade --ref v0.5.0-alpha
```

This also upgrades an earlier development installation to the alpha. On this
alpha, plain `omadora upgrade` stays on the same release. To move to a future
release, use that release's published tag explicitly. Personal configuration
is preserved; new default configuration is not automatically merged.

If the old installation lacks `upgrade`, use:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.5.0-alpha/boot.sh | bash -s -- upgrade
```

## Keybindings guide

Press **Super+K** (Windows+K) to open Omarchy's imported, searchable keybindings
guide. It is also available under **Omadora menu → Learn → Keybindings**.
Type to filter shortcuts; press Escape to close. The guide reads your Hyprland
bindings, including personal bindings. Omadora omits shortcuts for the stock
browser extensions that are not installed in its minimal profile.

## Recover

Run from GNOME or a TTY as the original installing user:

```bash
omadora rollback    # Restore the previous desktop after an upgrade
omadora recover     # Recover an interrupted install/update/rollback
```

These are separate actions; choose the one matching the problem. If the
launcher is unavailable, use the alpha bootstrap with `recover` or `rollback`
in place of `upgrade` above. To restore the original managed user settings,
use the actual backup path printed during installation:

```bash
omadora restore-config /path/to/your/backup
```

Later edits are preserved in a rescue backup. Desktop/config recovery does not
undo Fedora package transactions, repositories or OS changes, and is not a
full uninstaller. Details: [maintenance and recovery](MAINTENANCE.md).

## Report a problem

Include `omadora about`, Fedora/kernel versions, the failing action and its
error. For physical hardware, use the [read-only hardware kit](HARDWARE_TESTING.md)
and record actual observations. Review logs before sharing and omit credentials.
