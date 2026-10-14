# Development VM acceptance

This validation targets Fedora 44 x86_64, non-Atomic, in disposable QEMU VMs.
It checks Omadora's installation and desktop behavior. It does not certify all
third-party application workloads, accounts, games, AI models or physical GPUs.

## Desktop and installation

| Fixture | Result | Evidence |
| --- | --- | --- |
| KDE and Workstation package installation, recovery and upgrades | Pass; KDE starts with the exact old `kmime` RPM and the installer migrates it automatically | [Fedora integration](https://github.com/DanielCoffey1/omadora/actions/runs/38498862949) |
| KDE/SDDM login and logout | Eight checks pass, including wrong/correct greeter passwords, keyboard input after login, Plasma logout and logout with a queued graphical startup job | [KDE login](https://github.com/DanielCoffey1/omadora/actions/runs/38498464750) |
| KDE desktop, upgrade/rollback and recovery | 22 checks pass, including invisible capture proxy, full-width terminal, real pointer focus and paste | [Desktop suite](https://github.com/DanielCoffey1/omadora/actions/runs/38504358926) |
| KDE repeated login and suspend | Five SDDM restarts and three real guest S3 cycles pass, retaining the secure lock and normal password unlock | [Reliability](https://github.com/DanielCoffey1/omadora/actions/runs/38491706754) |
| KDE graphical wallpapers | Browse/apply/import/remove and default restoration pass; original imports retained | [Wallpapers](https://github.com/DanielCoffey1/omadora/actions/runs/38491706816) |
| Workstation startup after greeter race fix | Five successive GDM login checks pass | [Startup](https://github.com/DanielCoffey1/omadora/actions/runs/38497579931) |
| Workstation apps, keyboard, authentication and suspend | Pass; VS Code responds to New File and the secure lock survives wake | [Desktop/apps](https://github.com/DanielCoffey1/omadora/actions/runs/38496286460) |
| Official Workstation ISO installed through Anaconda | Desktop/recovery suite passes on the installed disk | [Fresh ISO](https://github.com/DanielCoffey1/omadora/actions/runs/38491820099) |
| Omadora offline ISO | Build, graphical install and boot with internet blocked pass at `0149502`, including the capture-proxy rules | [Offline ISO](https://github.com/DanielCoffey1/omadora/actions/runs/38502420568) |
| Mesa packages and earlier manual NVIDIA policy | Pass for the previous policy; superseded by [automatic NVIDIA setup](GRAPHICS.md) | [Earlier graphics run](https://github.com/DanielCoffey1/omadora/actions/runs/38489958578) |

The KDE fixture installs the real KDE package environment on the official Cloud
image. It is distinct from a fresh KDE ISO installation. The normal graphical
fixture uses the verified Bochs software display; explicit virtio diagnostics
remain available. See [VM graphics](VIRTUAL_MACHINES.md).
The fixture's emulated AMD CPU is unsupported by Fedora's `mcelog` hardware
collector, so its failure remains visible in terminal screenshots. These
results do not claim that every hardware diagnostic service passes in a VM.

The desktop suite exercises real upgrade/rollback login, one updater password
window, optional-app selection, Dictation installation and shortcuts, package
pickers, decoded screen recordings, reminders, 305 menu entries and 75 command
dependencies, the interactive keybindings guide, app logos, themes/bar positions,
toggles, window/workspace transitions, GTK/terminal clipboard, scaling, Activity,
screenshots, preserved font preferences, portal selection, network reconnect,
virtual audio controls, notifications and fallback/configuration recovery.

## Application entry points

The 93-entry catalog has 87 entries exercised at the entry-point level across
these suites. This is not 87 fully certified applications:

The [69-entry application results table](APP_VM_RESULTS.md) links each lifecycle
record to its VM evidence and preserves partial/unverified results explicitly.

- All 56 non-optional catalog entries have real install/presence/removal checks
  and a CLI, font or graphical startup probe. Existing base packages are retained.
- Another 13 optional font/CLI/desktop entries have the same VM probes. These
  include real font lookup and desktop startup, not just downloading an archive.
- Seven additional developer workflows execute their installed commands:
  Bun, Deno, Scala, Symfony, Laravel, Phoenix and OpenClaw. Hermes is included
  in the 13 optional VM entries. [Optional installation jobs](https://github.com/DanielCoffey1/omadora/actions/runs/38489958663),
  [refreshed Perplexity](https://github.com/DanielCoffey1/omadora/actions/runs/38491817811),
  [large archive/AppImage retests](https://github.com/DanielCoffey1/omadora/actions/runs/38495775087),
  [Hermes dependency retest](https://github.com/DanielCoffey1/omadora/actions/runs/38497077084).
- Five database workflows execute real queries and preserve queried data,
  credentials and named volumes across removal/reinstallation: PostgreSQL,
  MySQL, MariaDB, Redis and MongoDB. [Database VM](https://github.com/DanielCoffey1/omadora/actions/runs/38493665963).
- Five prompted workflows exercise real input and transactions: creating and
  launching a TUI, choosing a COPR/package, selecting Fira in the real optional
  picker, Xbox's browser launcher and Chromium's account launcher. No account
  is connected. [Interactive workflows](https://github.com/DanielCoffey1/omadora/actions/runs/38499547798).
- Dictation installation, model download, service restart and compositor
  shortcuts are exercised by the desktop suite. Physical transcription is separate.

Six entry points still require a separate manual scenario: Windows VM (licensed
ISO/KVM), ONCE deployment, Xbox controllers (hardware/kernel driver), Battle.net
(Lutris/game setup), RetroArch game launcher (ROM/core supplied by the user),
and SQL Server Developer (license choice). Their mapping, dependency resolution
and relevant guards have source/component coverage, not completed runtime acceptance.

Native GeForce NOW cannot start on the software GPU because it requires Vulkan
video decoding. Its installation/removal pass, but startup is explicitly recorded
as **NOT VERIFIED**, rather than treating its error window as a working app.
[NVIDIA troubleshooting](https://nvidia.custhelp.com/app/answers/detail/a_id/5737/kw/DYNAMIC).
Chrome reaches its terms dialog; the test does not accept those terms. Dropbox
reaches account setup, not synchronization. Zed's VM probe runs its packaged
editor with an explicit software-GPU opt-in. Account login, cloud gameplay,
model inference, paid deployments and third-party project execution are not
established by a startup screenshot.

## Fixes found during this pass

- Automatic `kmime` migration and KDE SDDM/X11 software greeter setup for the
  next boot, preserving other custom display managers and the running session.
- Greeter activation recovery limited to compositor startup and greeter sessions.
- Logout uses replacement job mode so queued Plasma startup jobs cannot reject it.
- KDE's X11 capture proxy gets invisible, floating, non-focusing window rules;
  its background process remains available for sharing.
- Java uses its concrete Fedora OpenJDK RPM for installed-status and removal.
- Perplexity's expired download is replaced with a current checksum-pinned artifact.
- Large optional extraction and AppImage temporary files use disk storage,
  avoiding Fedora's RAM-backed `/tmp` quota on small VMs.
- Optional installation resumes with a fresh interpreter if dependencies update
  Python while the installer is running.
- VM/ISO downloads use reachable origins; package verification remains enabled.

Autologin, fixture passwords, keyring initialization, account-setup completion
markers and queued-job fixtures are restricted to disposable tests. Omadora's
installer does not enable autologin or weaken password authentication.
