# Theme-colored application logos

`brands.json` maps application IDs to genuine monochrome brand artwork from
Simple Icons. Each SVG's pinned source URL and SHA-256 are recorded there;
the collection's CC0 license is in `brands/LICENSE.md`. Brand names and marks
remain their owners' trademarks. These icons identify optional applications.

`OmadoraAppIcons.ttf` contains only the selected logos. The menu loads it from
the deployed runtime with Qt's FontLoader, so it works before apps are installed
and after upgrades without changing the user's chosen fonts. The existing menu
renderer supplies the active theme's foreground and selected-text colors.
Install and Remove share each app's logo. Unmapped entries retain upstream
icons or their existing functional symbols.

Chromium, Chromium Account and Chrome share the same monochrome silhouette;
their colored versions differ. Codex CLI and ChatGPT use the OpenAI mark.
The Windows VM uses the Windows mark; Xbox integration uses Xbox's mark.
No unrelated same-name logos are used for TUI launcher or Hermes Desktop.

To reproduce the font from the checked-in SVG sources:

```sh
python3 -m pip install fonttools==4.65.0
python3 tools/build-brand-font.py
python3 tools/build-brand-font.py --check
```

FontTools is a development-only dependency; the installed desktop needs no
additional packages or network requests to render these icons.
