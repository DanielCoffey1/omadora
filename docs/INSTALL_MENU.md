# Install menu coverage

Minimal means apps are optional, not that their installers should be removed.
The original adapter replaced the whole upstream Install tree with 26 catalog
choices. The expanded catalog has 51 choices; none of these apps is preinstalled.
The base adds only explicit `file` and `desktop-file-utils` dependencies for
web-app icon checks and desktop launcher maintenance.
This remains a partial port of the pinned Omarchy 4.0.4 Install menu.

Catalog choices install Fedora/community/vendor RPMs or user-scoped Flatpaks and have matching
Remove entries. They do not automatically switch default browsers/editors,
install upstream plugins, start services, download AI models or configure
developer frameworks. Installed choices are hidden from Install.

## Restored choices

| Area | Available in Omadora |
| --- | --- |
| Package | Fedora package-name prompt using DNF with its normal transaction confirmation |
| Web App | Upstream launcher creation and removal; opens URLs in Firefox without Chromium app-window integration |
| Style | Theme import and current-theme background folder |
| Fonts | Cascadia Mono, Fira Code, Bitstream Vera Mono |
| Browser | Chrome, Edge, Brave, Zen, Chromium; Firefox is already part of the base desktop |
| Editor | VS Code, Zed, Sublime Text, Helix, Vim, Emacs |
| Terminal | Alacritty, Kitty, Ghostty (community COPR); Foot is already part of the base desktop |
| Services | Dropbox, Spotify, Signal, Bitwarden |
| Gaming | Steam, RetroArch, Minecraft Launcher, Lutris, Heroic, Bottles, MangoHud, GameMode, ProtonUp-Qt |
| Development | Podman, Node.js, Go, Rust, Ruby, Rails, Python development tools, PHP/Composer, Elixir, Zig, Java, .NET, OCaml/opam, Clojure |

Existing creative, media, productivity and communication choices remain.
Fonts here are Fedora font packages, not upstream Nerd Font downloads. Select
an installed face under Style → Font. The bundled Nerd font remains the fallback
for desktop icons. Flatpak editors can have toolchain and sandbox differences.
Ghostty uses the community COPR linked by its upstream documentation; the
repository is enabled only on request and remains configured after removal.
Sublime Text uses its official signed stable RPM repository. Selecting it imports
the vendor signing key and installs/refreshes that repository file; removing the
app leaves the key and repository configured for later installation.

## Remaining upstream entries

| Upstream choice | Remaining work |
| --- | --- |
| AUR | Arch-specific; Fedora package entry and explicit Flatpak catalog replace this role. No arbitrary COPR browser yet. |
| TUI | Launcher input validation and Foot-specific creation/removal |
| Meslo, Victor Mono, Iosevka | Verified Fedora 44 font sources |
| Windows | Fedora virtualization setup and VM lifecycle |
| Preinstalls | Intentionally omitted; individual optional choices replace the bundle |
| Brave Origin | Verified Fedora distribution |
| 1Password, Tailscale, NordVPN | Vendor repositories and desktop/service integration |
| ONCE | Fedora packaging |
| Chromium Account | Chromium-specific account integration |
| Cursor | Vendor RPM installation, updates and removal |
| Ollama, Scala | Packages absent in the tested Fedora 44 repositories; verified alternative sources needed |
| ChatGPT Desktop, Grok Bot, LM Studio, T3 Code, Hermes, OpenClaw, Perplexity | Fedora packaging and application-specific installation/lifecycle work |
| Dictation | voxtype packaging, models and audio integration |
| GeForce NOW | Verified Fedora-compatible distribution |
| Xbox Cloud Gaming | Browser/controller integration |
| Xbox Controllers | Kernel module packaging and Secure Boot testing |
| Battle.net | Lutris/Wine installation and removal workflow |
| RetroArch Game Launcher | Game launcher integration; RetroArch itself is available |
| Docker DB | Database container lifecycle; Podman is available separately |
| Bun, Deno | Versioned runtime installation |
| Laravel, Symfony, Phoenix | Framework-specific setup |

These entries are not exposed as working installers until ported. Availability
of an alternative does not establish exact upstream behavior parity.

## Sources and validation

Mappings use the pinned upstream menu, Fedora metadata and Flathub IDs.
Representative sources: [Ghostty Fedora installation](https://ghostty.org/docs/install/binary#fedora),
[Brave on Flathub](https://flathub.org/en/apps/com.brave.Browser), and
[Zed Flatpak integration](https://github.com/flathub/dev.zed.Zed).

The older [26-app runtime checks](APP_TESTS.md) do not cover newly added entries.
Package resolution, actual installation/removal and application launch are
separate levels of evidence; see [latest validation](VALIDATION.md).
