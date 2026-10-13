# KDE and Workstation VM checks

The VM workflows boot Fedora 44 under QEMU on a GitHub Actions Linux runner.
They use a checksum-verified Fedora Cloud disk with the requested desktop
package environment installed. This is not a fresh KDE ISO installation and
cannot reproduce a physical laptop's AMD/NVIDIA GPU, MUX or firmware.

## Verified fixes, October 13, 2026

[The corrected KDE run](https://github.com/DanielCoffey1/omadora/actions/runs/38464394854)
passed all seven checks at revision `a678e40`:

- Two lock cycles rejected wrong passwords and accepted the correct password;
  both shell status and the compositor confirmed the unlocked state.
- Window controls, clipboard and all power profiles passed.
- Dark/light/dark theme switching passed; the GTK light probe rendered a white
  background, instead of retaining the dark wallpaper palette.
- Normal Omadora logout and normal Plasma logout both returned to the greeter.
  Screenshots were visually inspected; the greeter display rendered.

[The diagnostic run](https://github.com/DanielCoffey1/omadora/actions/runs/38464199920)
identified the unlock cause: the shell reported `locked: true` even though
`requested`, `sessionLocked` and `secure` were false and the last event was
`unlocked`. Quickshell 0.3.2's native unlock implementation omits the lock-state
notification after releasing its lock. Omadora emits that notification after
normal authenticated unlock; it does not bypass PAM or destroy an active lock.
[Quickshell source](https://github.com/quickshell-mirror/quickshell/blob/v0.3.2/src/wayland/session_lock.cpp).

Theme switching now updates the managed GTK/Qt palette from the selected theme
under the theme transaction lock, after that theme becomes current. User CSS
is retained. The logout fixture now uses normal desktop logout commands rather
than forcibly terminating a logind session, which left Plasma services alive.

[The Fedora package suites](https://github.com/DanielCoffey1/omadora/actions/runs/38464396812)
also passed for KDE and Workstation, and Linux adapter/assembly/shell checks
passed. The previously reported KDE VM failures are resolved. This does not
establish a fix for the G14's physical GPU or its reported logout black screen.

## Earlier October 13, 2026 results

- [Workstation desktop/services/recovery](https://github.com/DanielCoffey1/omadora/actions/runs/38459144694): passed all 22 checks, including desktop upgrade/rollback login, clipboard, display scaling, screenshots, portal file chooser, audio and GNOME configuration recovery.
- [Full Fedora container installation](https://github.com/DanielCoffey1/omadora/actions/runs/38459467368): passed for KDE and Workstation identities. The historical release test runs only on Workstation because that historical release intentionally rejects KDE.
- [Initial KDE graphical run](https://github.com/DanielCoffey1/omadora/actions/runs/38459270157): installed successfully and reached Omadora, its menu and screensaver. Window controls, clipboard and power profile checks passed. Password unlock timed out although PAM logged successful authentication; GTK light theme rendered dark. Logout checks encountered a stale SSH-session lookup and QEMU GL screendump failure in the new fixture. This run is not a full pass.
- [KDE software-display rerun](https://github.com/DanielCoffey1/omadora/actions/runs/38461099418): installation and Omadora startup passed again. Window controls, clipboard, power profiles and Omadora logout to the KDE greeter passed; the greeter screenshot was visually inspected and rendered correctly. Plasma started and its desktop screenshot rendered correctly. Password unlock and GTK light-theme checks failed again. The Plasma logout check timed out waiting for `plasmashell` to exit; the journal shows the login greeter started, but the fixture did not capture a post-Plasma-logout screenshot. This is inconclusive for the reported black screen and is not a full pass.

## Repeat the KDE test

```bash
gh workflow run vm.yml --ref main -f edition=kde
```

The fixture uses Plasma Login Manager to start Omadora, performs desktop
interaction checks, logs out through the desktop command and captures the greeter.
It then starts Plasma and tests return to the greeter again. Autologin and
session selection are test instrumentation restricted to the disposable VM.
A running greeter process alone is not proof that the screen rendered:
inspect the saved screenshots and login-manager journal as well.

The workflow retains VM logs, per-check results and screenshots as artifacts,
including on failure. Physical GPU rendering and the G14 logout black screen
remain unvalidated by these VM results.
