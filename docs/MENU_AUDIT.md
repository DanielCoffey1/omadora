# Menu and shortcut audit

The minimal profile keeps the upstream desktop controls and supplies Fedora
Install/Remove/Update menus. This audit covers the generated menu, all six
default binding modules, dynamic font/application providers, and the helpers
behind retained shell panels. It does not prove every hardware or application
workflow works.

## Issues corrected

- Install and Remove entries now retain upstream icons or receive Nerd Font
  icons from the bundled font. Fedora package actions use a searchable,
  multi-select inventory and one reviewed DNF transaction. Web-app completion
  and package actions close with Enter.
- The recording indicator previously opened a filtered-out menu and checked
  for an uninstalled Arch recorder. It now opens Fedora recording choices and
  reads the owned `wf-recorder` process state; clicking while recording stops
  and finalizes the file. Reminder menu entries are restored. The Dictation
  indicator offers the optional installer when missing. Updates no longer
  opens a second terminal inside the first.
- The optional Install menu was reduced too far when creating the minimal base.
  It now includes 93 catalog entries and restores portable web-app/style
  installers. [Install coverage](INSTALL_MENU.md) records exact mappings,
  Fedora differences and interactive/hardware validation limits. Every pinned upstream Install action now has a mapping, including existing base Firefox and Foot.
- The shell menu had an embedded `pacman` package cache that shadowed the
  adapted RPM helpers. It now uses the installed Fedora helpers.
- Menu filtering now checks `checked` expressions as well as actions,
  visibility and disabled expressions.
- Install entries use the shell's supported `when` visibility condition, so
  installed apps disappear from Install and appear under Remove. The former
  `disabled` field was ignored by the upstream parser. Source checks now run
  the actual JavaScript parser and guard generator to catch schema mismatches.
- Hardware checkmarks repeat their visibility guard because upstream evaluates
  checkmarks even for hidden rows; absent vendor utilities are not invoked.
- Keybinding help no longer advertises the upstream browser extensions' copy
  URL and download-video shortcuts, since those extensions are not installed.
- The standalone Lua interpreter is installed so keybinding help can recover
  Lua dispatcher details and resolve numbered workspace shortcuts.
- `eject` supplies the media-eject key. `ddcutil` supplies the external display
  brightness helper. These are desktop utilities, not optional applications.
- The brightness router only selects the Apple vendor utility when it exists;
  otherwise it tries ordinary DDC/CI. Apple HID brightness support is not part
  of this release.
- Theme changes no longer invoke upstream browser-policy tinting, which sourced
  an excluded installer file and expected an upstream privileged entrypoint.
  Firefox follows the shared GTK light/dark preference; Chromium policy-based
  toolbar color synchronization is not supported.

## Coverage and limits

| Surface | Verification | Still requires validation |
| --- | --- | --- |
| Menu actions and predicates | Generated entries checked; runtime dependency and predicate inventory saved as `menu-audit.json` | User extensions and future upstream changes |
| Apps / Install / Remove | QML application provider; explicit Fedora catalog; prior catalog install/removal runs | Account login, gameplay, all app workflows and offline cases |
| Learn and About | Targets point to Omadora, Fedora, Hyprland, Bash and plain Neovim | External website availability |
| Fonts, theme and background | Existing font test plus theme/background change-and-restore checks | Full application visual parity |
| Bar and toggles | Position, transparency, idle, nightlight, screensaver, bar, gaps, layout and notification state checks | Physical display color output and idle timing |
| Screenshot / color | Screenshot keyboard cancellation and clipboard equality tested; `hyprpicker` available | Color selection and every region-picker combination |
| Audio / network | Virtual audio volume/mute and network reconnect tests | Physical audio, Wi-Fi authentication and Bluetooth pairing |
| Display / power / Bluetooth panels | Display renders with fixed VM brightness; keyboard scaling changes 1x to 1.25x and back using the default monitor rule; Bluetooth renders “No adapter”; upstream power panel stays hidden without a battery | Custom monitor rules, monitor topology, DDC permissions/hardware, battery panel/profile controls and radio hardware |
| Window and clipboard shortcuts | Real key input creates two Foot windows, toggles fullscreen/floating, moves a window to workspace 2 and closes it; Super+C/X/V works in a GTK entry; Super+V pastes exact text into Foot | Grouping, other tiling combinations, other applications and multi-monitor behavior |
| System actions | Prior lock/password and Bochs suspend tests; logout/reboot/shutdown helpers use UWSM/systemd | Full power-action sequence on physical hardware; virtio suspend issue remains |
| Speed tests | Network uses curl/IP tools; disk uses bounded temporary files and standard utilities | Fast.com availability and real disk throughput run |

Optional application bindings remain disabled. Dictation bindings require an
installed `voxtype`; Dell haptics require both matching hardware and the
vendor command. Theme hooks for omitted apps generally exit when their app or
configuration is absent; this does not establish compatibility for manually
installed upstream-only apps such as Hermes.

`tests/fedora-menu-audit.py` checks command availability and evaluates menu
predicates in the disposable Fedora session. False hardware predicates are
recorded as false, not counted as successful hardware tests. The graphical
suite captures menus and panels for inspection and tests state transitions;
merely opening a panel does not validate its hardware controls.

The earlier VM audit inventories 136 menu entries, 73 executable dependencies,
64 evaluated predicates, and 187 lines of shortcut help. Hardware checkmark
queries short-circuit when their hardware condition is false. The shortcut help
count is an inventory, not 187 individually executed shortcut tests.
Those counts predate the optional Install expansion; its new mappings have
source/parser and Fedora package-resolution coverage, not a new graphical audit.

See [validation results](VALIDATION.md) for workflow evidence and
[compatibility](COMPATIBILITY.md) for remaining release limitations.
