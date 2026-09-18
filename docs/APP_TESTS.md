# Optional application validation

Tested on September 17, 2026 in the booted Fedora 44 Workstation-package VM described in [VALIDATION.md](VALIDATION.md). These are installation, presence-query, removal and basic launch checks. They do not establish gameplay, media capture/playback, account login, container workloads or complete application compatibility.

Every original 26-entry catalog install command passed, as did every removal attempted. The Lutris dependency fix is verified; Chromium and GIMP reached their main interfaces in the retest. Later runs confirmed Steam's client download and sign-in screen, Signal's linking screen, Discord's login form, and corrected sandbox font lookup. Account and gameplay workflows remain unverified. The tables below retain historical failures; subsequent retests record their resolution.

The expanded 51-entry catalog adds apps not covered by these historical runtime results. See [Install coverage](INSTALL_MENU.md) and [latest validation](VALIDATION.md).

## Original catalog run

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

## Font and startup retest

[Run 35242929475](https://github.com/DanielCoffey1/omadora/actions/runs/35242929475), at `e95ca23`, installed and removed Steam, Signal, Discord and Bottles successfully. Sandboxed font lookup passed in all three Flatpaks, without the previous inaccessible-host-path error. Discord's screenshot showed the complete login form; Bottles showed its welcome interface in dark styling. No account was used.

Steam still did not open. Its newly collected `console-linux.txt` reported inability to load trusted SSL root certificates, and `bootstrap_log.txt` recorded failure to download the client manifest. Exposing the host CPU to the VM did not resolve this failure. Fedora documents the [removal of the legacy certificate bundle paths](https://fedoraproject.org/wiki/Changes/droppingOfCertPemFile), and Valve tracks the [matching Fedora Steam issue](https://github.com/ValveSoftware/steam-for-linux/issues/12318).

Signal's test mistakenly accepted the dialog's default No button. The wrapper log explicitly reported an abort at the user's choice; this is a harness error, not evidence of an application crash. The corrected test selects Yes only in the disposable empty test profile, without linking an account or changing Omadora's storage configuration.

The [Steam/Signal retest](https://github.com/DanielCoffey1/omadora/actions/runs/35246575064), at `80be428`, passed both installation/removal transactions. Signal reached its actual QR-code linking screen after the test selected Yes; no account was linked. Steam still failed with the same root-certificate error when launched through an experimental `SSL_CERT_FILE` wrapper. That approach was ineffective and has been removed, along with its custom desktop entry. The replacement creates the legacy certificate-path symlink only when Steam is installed, points it at Fedora's maintained bundle, and preserves any existing path. It does not use the deprecated `update-ca-trust` compatibility flag or disable verification.

## Native Steam fix verified

[Run 35249426231](https://github.com/DanielCoffey1/omadora/actions/runs/35249426231), at `0eeeebd`, installed Steam through Omadora, verified the live certificate link, launched the RPM's original desktop entry using `gtk-launch steam`, and removed Steam successfully. The client downloaded and installed its approximately 496 MB update, restarted, and rendered the complete **Sign in to Steam** window. The screenshot was reviewed, and the collected client logs no longer contain the former trusted-root loading error. No account was used and no game was run. Persistence of the compatibility link across a later `ca-certificates` package upgrade has not been tested.

The five ordinary desktop checks also passed, including resolved GTK dark/light/dark background colors. The overall workflow is failed because the subsequent S3 test still could not unlock after resume; Steam's independent pass does not change that result.

## Remaining limits

Signal's Flatpak launcher displays a warning about its default plaintext password store. The latest test proceeded to the linking screen in an empty disposable profile; it did not change the storage setting or link an account. Keyring prompts in other apps were observed in the empty autologin fixture; account and keyring workflows remain untested.

The former session-wide `FONTCONFIG_FILE` override has been removed. Signal, Discord and Bottles passed the sandbox font check after this correction; the other Flatpaks have not all been rerun with the new configuration. The native GTK file chooser's dark styling is now verified in the [theme/recovery retest](https://github.com/DanielCoffey1/omadora/actions/runs/35248151319); full application font/theme parity is still incomplete. GameMode's earlier CPU-governor self-test failed in the VM; its version-command pass does not supersede that result.

Raw per-app logs, window identities, screenshots, `apps/results.json`, and the later interaction results are available in each run's `fedora-vm-results` artifact. The raw launch labels should be interpreted using the reviewed results above.
