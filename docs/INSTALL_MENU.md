# Install menu coverage

The catalog contains 93 optional choices. Every actionable Install entry in the
pinned Omarchy 4.0.4 menu now has a Fedora mapping; Firefox and Foot are already
in the base desktop. An automated test compares the upstream menu with the
generated menu to prevent omissions. Menu coverage does not establish complete
application or hardware compatibility.

Nothing from this catalog is installed by the base profile. The upstream
Preinstalls action becomes **Optional apps**, an explicit multi-select
picker. Selecting a category never installs a bundle.

## Mappings

| Area | Fedora implementation |
| --- | --- |
| Package / AUR | Searchable available RPM list; AUR becomes a validated COPR owner/project and package prompt |
| TUI / Web App | Foot launchers for installed terminal commands; Firefox web launchers |
| Theme / Background | Upstream theme import and current-theme background folder |
| Fonts | Fedora Cascadia Mono, Fira Code and Bitstream Vera Mono; pinned Meslo, Victor Mono and Iosevka Nerd Font archives |
| Browser | Chrome, Edge, Brave, Brave Origin, Zen and Chromium; Firefox is in the base |
| Editor | VS Code, Zed, Sublime Text, Helix, Vim, Emacs and Cursor |
| Terminal | Alacritty, Kitty and Ghostty; Foot is in the base |
| Services | Dropbox, Spotify, Signal, Bitwarden, 1Password, Tailscale, NordVPN, ONCE and Chromium Account |
| AI | Codex CLI, Claude Code, Ollama, ChatGPT Desktop, Perplexity, Grok Bot, T3 Code, LM Studio, Hermes Desktop, OpenClaw and Dictation |
| Gaming | Steam, RetroArch, Minecraft, Lutris, Heroic, Bottles, MangoHud, GameMode, ProtonUp-Qt, GeForce NOW, Xbox Cloud Gaming, Xbox Controllers, Battle.net setup and RetroArch Game Launcher |
| Development | Existing Fedora language packages plus Bun, Deno, Scala/compiler/Scala CLI, Laravel, Symfony and Phoenix |
| Databases | Rootless Podman PostgreSQL, MySQL, MariaDB, Redis, MongoDB and SQL Server Developer containers |
| Windows | Per-user libvirt/QEMU/KVM VM with UEFI and TPM 2.0; user supplies a licensed Windows ISO |

Creative, media, productivity and communication choices remain. The complete
catalog is [apps.json](../apps.json); download pins and workflow versions are in
[optional.json](../optional.json).

## Installation and removal

**Fedora package** lists packages from enabled repositories under Install and
all installed RPM names under Remove. Type to narrow the list, press Tab to
select several packages, and press Enter to review the DNF transaction. Escape
cancels. DNF still previews dependencies and asks for confirmation before
changing packages. Its protected-package rules remain enabled.

Every Install and Remove menu entry has an icon. Web-app installation and the
package picker finish with **Press Enter to close this window**.

Native apps use Fedora, RPM Fusion, explicit COPRs or vendor RPM repositories.
Vendor signing checks remain enabled. Repository files and signing keys remain
after package removal. Tailscale and NordVPN services start when requested;
NordVPN group changes require signing in again. Account connection is manual.
Ghostty uses the community `scottames/ghostty` COPR. GeForce NOW uses NVIDIA's
official Flatpak remote; other Flatpaks use the user's Flathub remote.

Apps without an appropriate RPM/Flatpak use versioned downloads verified by
SHA-256 or SHA-512. Some vendors distribute their Linux payload inside a Debian
archive: Omadora extracts the payload into per-user storage, installs Fedora
library dependencies and creates its own launcher. It never runs Debian package
scripts. AppImages run with extraction enabled. These adaptations need graphical
workload testing in addition to extraction and dependency checks.

Managed files live under `~/.local/share/omadora/optional/`, with command wrappers
under `~/.local/bin`. Existing foreign commands and launchers are not overwritten.
Failed launcher registration can resume without downloading the payload again.
Removal retains personal profiles, AI models, games, VM disks and database
volumes. Dependency packages and the shared Mise helper remain available.
Remove/reinstall applies a newer committed download pin; pinned payload updates
are not part of DNF. Package dependencies and container tags are not immutable
release locks.

Ordinary installed entries disappear from Install and appear under Remove.
Repeatable launchers, COPR package selection and the optional-app picker remain
available. COPR packages are removed through the Fedora package prompt. Removing
TUI or RetroArch Game Launcher removes all launchers created by that wizard,
while preserving terminal programs, ROMs, cores and RetroArch itself.

## Workflow differences and limits

- Windows creates an 8 GB RAM, 4 CPU, 64 GB disk VM using the user's libvirt
  session. It requires working KVM access. Guest installation and Windows
  licensing are separate; existing VM disks are retained on removal.
- ONCE installs Fedora Moby/Docker compatibility packages and a root-owned
  background service. ONCE-managed applications and data survive removal.
- Chromium Account creates a dedicated browser launcher. Google controls
  whether its account integration is accepted.
- Battle.net opens Lutris's installer; completing game setup is interactive.
  The catalog's installed state means the setup launcher exists, not that a
  Battle.net installation or game has been verified.
- Xbox Controllers builds xpadneo with DKMS against the running Fedora kernel.
  Secure Boot can require manual MOK enrollment and a reboot. Bluetooth pairing,
  controller hardware and module signing are not validated in container tests.
- Dictation uses the native Voxtype RPM and its model/service setup. Microphone
  input, model inference and dictation need a live desktop test.
- Developer installers isolate Mise, Composer and Mix files from project
  directories. OpenClaw uses a compatible private Node runtime; first launch
  opens onboarding. Account authorization and AI workloads remain manual.
- Database ports bind to loopback. Credentials use a private mode-0600 file;
  named Podman volumes persist after removal. MySQL and MariaDB share port 3306,
  so stop one before starting the other. SQL Server asks for license acceptance.
- Fedora fonts are not identical to every upstream Nerd Font variant; the
  bundled Nerd font remains the desktop icon fallback. Flatpak editors retain
  sandbox/toolchain differences.

See [validation](VALIDATION.md) for package resolution, real install/remove
checks, command launches and graphical tests, recorded separately.

## Sources

Pinned upstream menu and scripts: [Omarchy 4.0.4](https://github.com/omacom/omarchy/tree/v4.0.4).
Vendor download URLs/checksums were cross-checked against
[Omarchy packaging recipes](https://github.com/omacom/omarchy-pkgs/tree/03ef2e3ef7b2219fae97b1c2578a99d4cd9e3f8f).
Those Arch recipes are not executed by Omadora. Official references include
[Brave Origin](https://brave.com/origin/linux/),
[1Password](https://support.1password.com/install-linux/),
[Tailscale](https://pkgs.tailscale.com/stable/),
[Voxtype](https://voxtype.io/download), and
[xpadneo](https://github.com/atar-axis/xpadneo).

Codex CLI and Claude Code use pinned, checksum-verified official Linux binaries
and open in Foot. The `codex` and `claude` commands are available in the terminal.
Their account/configuration directories are preserved on removal. Claude self-updates
are disabled for this managed copy; update the Omadora recipe and remove/reinstall
to apply a newer pin. Sign-in and model requests remain user-driven. Sources:
[Codex CLI](https://learn.chatgpt.com/docs/codex/cli) and
[Claude Code setup](https://code.claude.com/docs/en/setup).

Codex CLI and Claude Code use pinned, checksum-verified official Linux binaries
and open in Foot. The `codex` and `claude` commands are available in the terminal.
Their account/configuration directories are preserved on removal. Claude self-updates
are disabled for this managed copy; update the Omadora recipe and remove/reinstall
to apply a newer pin. Sign-in and model requests remain user-driven. Sources:
[Codex CLI](https://learn.chatgpt.com/docs/codex/cli) and
[Claude Code setup](https://code.claude.com/docs/en/setup).
