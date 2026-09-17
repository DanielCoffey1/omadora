# Third-party sources

- Desktop: https://github.com/omacom/omarchy at v4.0.4 / `c668141e9c42b13c80c9ca4ea108e11708c5e8a5`. MIT license copied unmodified on assembly. The installer does not execute upstream install or migration scripts.
- Hyprland ecosystem COPR: https://copr.fedorainfracloud.org/coprs/nett00n/hyprland/ . Community package source; Fedora 44 resolution needs validation.
- Screensaver RPM: https://copr.fedorainfracloud.org/coprs/whelanh/omarchy/ . Only `ttfx` is selected from the first-party application set; the package repository itself is community maintained.
- Reference research: https://github.com/whelanh/omarchy-fedora . Its Fedora package mappings and UWSM/PAM compatibility notes informed the design. Omadora's adapter was written independently; that project's installer is not executed or vendored.
- Existing unrelated same-name project: https://github.com/elpritchos/omadora . Not this repository's upstream.
- Nerd Font: see `assets/fonts/README.md` and `OFL.txt`.
- Steam repository setup: https://rpmfusion.org/Configuration . Added only when Steam is requested; repository signature checks stay enabled.
- Heroic Flatpak source: https://github.com/flathub/com.heroicgameslauncher.hgl . Other Flatpak application IDs are listed explicitly in `apps.json`.

Omadora is not an official release of Fedora, Omarchy or any third-party application.
