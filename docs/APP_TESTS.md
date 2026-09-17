# Optional application validation

Tested on September 17, 2026 in the booted Fedora 44 Workstation-package VM described in [VALIDATION.md](VALIDATION.md). These are installation, presence-query, removal and basic launch checks. They do not establish gameplay, media capture/playback, account login, container workloads or complete application compatibility.

Current result: every catalog install command passed, as did every removal attempted. The Lutris dependency fix is verified; Chromium and GIMP reached their main interfaces in the retest. Steam launch failed in this VM. Signal stopped at its wrapper warning, and Discord's captured main window still showed a loading indicator, so those account/startup flows remain unverified.

## Full catalog run

[Run 35234023393](https://github.com/DanielCoffey1/omadora/actions/runs/35234023393), commit `b578c75`, exercised all 26 entries through the real Omadora CLI and interactive package managers:

- All 26 install commands succeeded and the installed-package queries passed.
- All 23 attempted removals succeeded and the installed queries then returned absent.
- GameMode, Podman and Node.js were already present when their checks started, so their removal was intentionally not attempted.
- The automated launch check initially accepted any new window. Reviewing window identities and screenshots downgraded four preliminary dialogs/splashes; the table below records the reviewed result, not the overly broad raw pass count.
- The overall workflow failed. Lutris and Chromium did not launch, and the later suspend/unlock check failed again. Authentication, keyboard/windows, clipboard, power-profile switching and themes passed before suspend.

| Application | Install | Reviewed launch result | Remove |
| --- | --- | --- | --- |
| Steam | Pass | Preliminary setup only; main client unverified | Pass |
| Lutris | Pass | Fail: missing `xrandr` caused a Python traceback | Pass |
| Heroic | Pass | Application/library and release-notes dialog | Pass |
| Bottles | Pass | Application and welcome screen | Pass |
| MangoHud | Pass | Version command | Pass |
| GameMode | Pass | Version command only | Not attempted: already present |
| RetroArch | Pass | Application window | Pass |
| ProtonUp-Qt | Pass | Application window | Pass |
| OBS Studio | Pass | Application and configuration wizard | Pass |
| GIMP | Pass | Startup splash only; editor unverified | Pass |
| Kdenlive | Pass | Application's quick-setup screen | Pass |
| VLC | Pass | Application and privacy dialog | Pass |
| Spotify | Pass | Application window | Pass |
| LibreOffice | Pass | Writer and welcome dialog | Pass |
| Obsidian | Pass | Vault-selection screen; keyring prompt also appeared | Pass |
| Bitwarden | Pass | Login screen; keyring prompt also appeared | Pass |
| Signal | Pass | Flatpak wrapper warning only; main application unverified | Pass |
| Discord | Pass | Updater only; main application unverified | Pass |
| Visual Studio Code | Pass | Editor with the Flatpak package's information page | Pass |
| Podman | Pass | `podman info` | Not attempted: already present |
| Node.js | Pass | `node --version` | Not attempted: already present |
| Rust | Pass | `rustc --version` | Pass |
| Go | Pass | `go version` | Pass |
| Kitty | Pass | Terminal window | Pass |
| Alacritty | Pass | Terminal window | Pass |
| Chromium | Pass | Test invoked nonexistent `chromium` executable | Pass |

## Corrections and limitations

The Lutris optional package selection now includes Fedora's [`xrandr`](https://packages.fedoraproject.org/pkgs/xrandr/xrandr/fedora-44.html). The captured traceback showed Lutris passing an absent executable to its display-mode probe. This dependency is optional with Lutris, not added to Omadora's minimal core.

The Chromium test now invokes Fedora's [`chromium-browser`](https://packages.fedoraproject.org/pkgs/chromium/chromium/fedora-44.html). The Chromium package installed correctly; this was a test-command error.

Launch checks now require the expected application's window class and reject known startup/updater titles. Steam is allowed five minutes for its first-run client download. Window creation still needs screenshot review and does not establish application readiness.

## Focused retest

[Run 35237031270](https://github.com/DanielCoffey1/omadora/actions/runs/35237031270), commit `eb6b7fa`, repeated a fresh installation using the public one-line command. All five selected entries installed and were removed successfully:

| Application | Reviewed retest result |
| --- | --- |
| Lutris | Pass: library/welcome interface rendered after installing the optional `xrandr` dependency |
| Chromium | Pass: New Tab page rendered using `chromium-browser`; a new-keyring prompt was also present |
| GIMP | Pass: editor interface and welcome dialog rendered, beyond the startup splash |
| Discord | Application window rendered beyond the updater, but the screenshot still showed a loading indicator; completed login/account flow unverified |
| Steam | Fail: no main application window appeared within five minutes; the guest journal recorded two assertion minidump uploads during launch |

Steam's root cause is not established by the collected log. Its successful RPM transaction must not be presented as a successful Steam launch. No compatibility override or replacement package source was enabled to hide the failure.

The corrected Network menu action opened the native Ethernet panel and its screenshot was reviewed. The panel's ping probe showed a timeout in the QEMU network fixture; DNS switching and Wi-Fi were not tested. The separate service suite verified HTTPS connectivity after reconnection. Authentication, keyboard/windows, clipboard, power profiles and theme switching passed again. Suspend/resume failed at post-resume unlock again, so this workflow is correctly marked failed overall.

## Remaining limits

Signal's Flatpak launcher displayed a warning about its default plaintext password store. The test stopped at that wrapper dialog; it did not change the storage setting, link an account or verify Signal's main window. Keyring prompts in other apps were observed in the empty autologin fixture; account and keyring workflows remain untested.

Several sandboxed applications logged that the session's `FONTCONFIG_FILE` points to a host configuration file they cannot read. Their captured interfaces rendered text, but this is an unresolved font-integration warning, not evidence of complete font/theme parity. The GTK light-style discrepancy is tracked in the main validation record. GameMode's earlier CPU-governor self-test failed in the VM; its version-command pass does not supersede that result.

Raw per-app logs, window identities, screenshots, `apps/results.json`, and the later interaction results are available in each run's `fedora-vm-results` artifact. The raw launch labels should be interpreted using the reviewed results above.
