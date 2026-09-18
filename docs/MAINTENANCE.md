# Desktop updates and recovery

Log out of every Hyprland session and use GNOME or a TTY for these commands. Omadora refuses maintenance while a Hyprland process is running. Keep enough free space on `/usr` and `/var` for staged copies and snapshots of the desktop. These commands manage Omadora's desktop files; they do not roll back Fedora packages or the operating system.

## Upgrade

```bash
omadora upgrade --ref v0.1.0-alpha
```

The command fetches `v0.1.0-alpha` from `DanielCoffey1/omadora`, then runs its update code. On this alpha, plain `omadora upgrade` also stays on that release. Use `--ref NAME` to choose a future published tag explicitly. Development installs may deliberately use `--ref main`; older development versions defaulted to `main`, so specify the alpha tag when upgrading them. This uses the same repository trust as the installer; it is not yet a signed package-release channel.

The updater assembles the pinned Omarchy source before changing the desktop. Required RPM dependencies must install successfully. A root-owned journal snapshots the existing runtime, launcher links, PAM file and GDM session file. The new runtime must pass Hyprland configuration validation with your actual configuration. Errors trigger recovery; the GDM entry is published only after validation. Log into Omadora to use the new desktop.

Updates preserve personal config files, the selected theme/font, user fonts and shared GTK settings. They do not overwrite or automatically merge new upstream user-config defaults. A future incompatible configuration migration needs its own implementation; this updater does not claim support for arbitrary Omarchy major-version jumps.

For an older installation without the command, use:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.1.0-alpha/boot.sh | bash -s -- upgrade
```

Developers can run `python3 omadora.py upgrade --local` from a trusted source checkout without fetching the repository again.

## Diagnose unavailable Super/Windows shortcuts

If shortcuts stop working, open Foot using the menu/mouse and capture
`hyprctl configerrors` before restarting the session. Check Super+Return and
Super+Space separately from pressing Super alone. If Dictation is installed,
temporarily run `systemctl --user stop voxtype.service` and check those same
shortcuts again. Restore Dictation with `systemctl --user start voxtype.service`.
Record whether stopping the service, logging out, or rebooting changes the
result. This isolates the service without deleting your configuration; a
reboot restoring the keys does not by itself establish the cause.

## Return to the previous desktop

```bash
omadora rollback
```

One previous system-desktop snapshot is retained after a successful upgrade. Rollback validates it against your current personal configuration before completing. Your personal edits remain; Fedora RPMs and repositories remain. If validation fails, recovery returns to the runtime that was installed when rollback began. A successful rollback retains that runtime as the new previous snapshot, allowing the operation to be reversed.

Use the bootstrap with `rollback` if the installed command is unavailable, including after restoring a legacy desktop that predates the lifecycle commands.

## Interrupted install or update

```bash
omadora recover
```

If the launcher was not yet created, or an interruption occurred during runtime replacement, use:

```bash
curl -fsSL https://raw.githubusercontent.com/DanielCoffey1/omadora/v0.1.0-alpha/boot.sh | bash -s -- recover
```

A saved source checkout also works offline: `python3 /path/to/omadora/omadora.py recover`. Use the same regular user who started the operation.

Recovery before commit restores the prior system desktop. For an interrupted first install, it also restores the original managed user configuration and font directory, preserving later files in a rescue backup. During an interrupted upgrade or rollback, personal configuration is left untouched. If validation and the commit decision had already completed, recovery finishes committing the new desktop instead of undoing it. Recovery itself can be retried after interruption. A second install/update is refused while a journal is pending.

Root snapshots live under `/var/lib/omadora`; the matching user journal and configuration backups live under `~/.local/state/omadora`. Do not delete those snapshots while recovery is pending. Free disk space or correct filesystem errors if recovery cannot finish, then retry. DNF transactions, repository enablement and package downloads are retained even when desktop deployment is rolled back.

Installations interrupted before journaled deployment was introduced have only their original configuration backup. They cannot be safely reconstructed by the new recovery command: use `restore-config` for their saved settings and inspect remaining system files before cleanup. This feature is not a general uninstaller, OS snapshot system, or guarantee against storage corruption.
