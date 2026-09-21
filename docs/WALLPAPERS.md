# Wallpapers and generated colors

Omadora uses wallpaper-driven dark palettes instead of the preset theme picker.
Fresh installations start with **Nepal_5160x2160.png** from the supplied collection.
pywal16 3.8.15 (the maintained pywal fork, command `wal`) is bundled with the
installed runtime. Fedora installs ImageMagick, Pillow, GTK4 and Qt6ct alongside it.

## Menu

- **Style → Wallpapers & colors**: search the 332 previews and click an image to apply it.
- **Install → Style → Add wallpapers**: select one or several local images.
- **Remove → Remove wallpapers**: choose an image and confirm removal.

The browser also has Add wallpapers and Remove selected buttons. Right-click a
preview to select it for removal without applying it. Imported originals are
never deleted: Omadora owns a copy. Removing the active wallpaper first switches
to Nepal (or another remaining image if Nepal was removed). At least one image
must remain. Adding a removed bundled image again restores it to the library.

Previews and Nepal are bundled. Other full-size images download on first selection
from the pinned wallpaper asset release, are verified by SHA-256, and stay cached.
Browsing works offline; selecting an uncached image needs Internet access. A failed
download or extraction leaves the prior palette in place. Files are in
`~/.local/share/omadora/wallpapers` and `~/.cache/omadora/wallpapers`.

## Color coverage

The palette feeds Omadora's existing templates for the shell/bar, menus,
notifications, lock screen, Hyprland borders, Foot and other supported terminals,
Neovim, and supported optional apps. The same colors generate GTK3/GTK4 CSS and a
Qt6ct palette. Toolkit apps may need reopening after a change. Individual app CSS
or custom themes can override these colors. Flatpak sandboxes, browser content,
apps with their own theme engines, and Fedora's separate GDM login account are
not guaranteed to use the generated colors.

Existing GTK CSS is retained with one managed import. Toolkit files are included
in desktop maintenance backups. Wallpaper library contents are user data and are
retained during rollback. The previous generated state is restored on an apply
failure; live apps may need reopening if their theme hook had already run.

Upgrades preserve an existing selected theme until you choose a wallpaper from
the new browser. The Nepal default applies to fresh installations. User-added
wallpapers and their selected palette survive subsequent upgrades.

## Commands

```bash
omadora wallpaper browse
omadora wallpaper add /path/to/image.png
omadora wallpaper apply Nepal_5160x2160.png
omadora wallpaper list
omadora wallpaper remove WALLPAPER_ID
omadora wallpaper next
```

`wal` is available in the Omadora session PATH. Use `omadora wallpaper apply` to
update the whole supported desktop; running plain `wal` only updates its own
outputs. The generated theme is stored at
`~/.config/omarchy/themes/omadora-wallpaper`; edit the wallpaper library through
the menu rather than hand-editing generated theme files.
