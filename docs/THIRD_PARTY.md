# Third-party sources

- Desktop: https://github.com/omacom/omarchy at v4.0.4 / `c668141e9c42b13c80c9ca4ea108e11708c5e8a5`. MIT license copied unmodified on assembly. The installer does not execute upstream install or migration scripts.
- Hyprland ecosystem COPR: https://copr.fedorainfracloud.org/coprs/nett00n/hyprland/ . Community package source; Fedora 44 resolution needs validation.
- Screensaver RPM: https://copr.fedorainfracloud.org/coprs/whelanh/omarchy/ . Only `ttfx` is selected from the first-party application set; the package repository itself is community maintained.
- Reference research: https://github.com/whelanh/omarchy-fedora . Its Fedora package mappings and UWSM/PAM compatibility notes informed the design. Omadora's adapter was written independently; that project's installer is not executed or vendored.
- Existing unrelated same-name project: https://github.com/elpritchos/omadora . Not this repository's upstream.
- Nerd Font: see `assets/fonts/README.md` and `OFL.txt`.
- Application logos: Simple Icons artwork, redistributed under CC0 in `assets/icons/brands`. Each selected SVG's pinned source and checksum are in `assets/icons/brands.json`; see [logo font details](../assets/icons/README.md).
- Steam repository setup: https://rpmfusion.org/Configuration . Added only when Steam is requested; repository signature checks stay enabled.
- Heroic Flatpak source: https://github.com/flathub/com.heroicgameslauncher.hgl . Other Flatpak application IDs are listed explicitly in `apps.json`.

Omadora is not an official release of Fedora, Omarchy or any third-party application.

Wallpaper colors use [pywal16](https://github.com/eylles/pywal16) 3.8.15 (MIT),
bundled from the verified PyPI wheel recorded in `vendor/pywal16.lock.json`.
Its license and distribution metadata are retained alongside the module.
ImageMagick performs palette extraction; Fedora packages provide GTK4, Pillow
and Qt6ct. No root pip installation is used.

The 332 wallpapers were supplied by the project owner from their
`aesthetic-wallpapers-main/wallpapers/images` collection. Omadora does not claim
authorship or relicense those images under its code license. The catalog records
original filenames and SHA-256 checksums; the wallpaper asset release holds the
full-size originals and the repository holds generated previews plus the Nepal
default.

Optional download URL/checksum research also used
[omacom/omarchy-pkgs at 03ef2e3](https://github.com/omacom/omarchy-pkgs/tree/03ef2e3ef7b2219fae97b1c2578a99d4cd9e3f8f).
Arch build/install recipes are not executed. Downloaded applications and fonts
retain their upstream licenses; Omadora's license does not relicense them.
`optional.json` records URLs, hashes and selected tool versions. Vendor RPM
repositories are stored under `assets/repos`; package signature checks remain
active. See [Install sources and differences](INSTALL_MENU.md).
