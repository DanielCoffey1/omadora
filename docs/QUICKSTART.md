# Omadora v0.2.0-alpha quick start

Target: fresh Fedora Workstation **44, x86_64**, non-Atomic. This is an alpha
release of the minimal Omarchy 4.0.4 desktop port. GNOME and Fedora's existing
apps remain available. See [known limits](releases/v0.2.0-alpha.md).

## Install

From a terminal as your regular Fedora user:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.2.0-alpha/boot.sh | bash
```

The bootstrap defaults to fetching `v0.2.0-alpha`, not `main`. Leave
`OMADORA_REF` unset for this release; it is an explicit source override for
developers. The installer requests sudo for packages/system files, enables the
documented desktop COPRs and backs up managed user configuration. Save the
backup path it prints. Internet access is required.

After installation, log out. Select your user in GDM, choose **Omadora** in
the gear menu, and log in. Check the version with `omadora about`. Use the
desktop's **Install** menu for optional apps, including Gaming and AI.

## Update

Fedora packages: `omadora update`. Optional user Flatpaks: `flatpak update --user`.

For Omadora itself, log out of all Hyprland sessions and enter GNOME or a TTY:

```bash
omadora upgrade --ref v0.2.0-alpha
```

This also upgrades an earlier development installation to the alpha. On this
alpha, plain `omadora upgrade` stays on the same release. To move to a future
release, use that release's published tag explicitly. Personal configuration
is preserved; new default configuration is not automatically merged.

If the old installation lacks `upgrade`, use:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.2.0-alpha/boot.sh | bash -s -- upgrade
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
