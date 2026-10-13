# KDE and Workstation VM checks

The VM workflows boot Fedora 44 under QEMU on a GitHub Actions Linux runner.
They use a checksum-verified Fedora Cloud disk with the requested desktop
package environment installed. This is not a fresh KDE ISO installation and
cannot reproduce a physical laptop's AMD/NVIDIA GPU, MUX or firmware.

## October 13, 2026 results

- [Workstation desktop/services/recovery](https://github.com/DanielCoffey1/omadora/actions/runs/38459144694): passed all 22 checks, including desktop upgrade/rollback login, clipboard, display scaling, screenshots, portal file chooser, audio and GNOME configuration recovery.
- [Full Fedora container installation](https://github.com/DanielCoffey1/omadora/actions/runs/38459467368): passed for KDE and Workstation identities. The historical release test runs only on Workstation because that historical release intentionally rejects KDE.
- [Initial KDE graphical run](https://github.com/DanielCoffey1/omadora/actions/runs/38459270157): installed successfully and reached Omadora, its menu and screensaver. Window controls, clipboard and power profile checks passed. Password unlock timed out although PAM logged successful authentication; GTK light theme rendered dark. Logout checks encountered a stale SSH-session lookup and QEMU GL screendump failure in the new fixture. This run is not a full pass.
- [KDE software-display rerun](https://github.com/DanielCoffey1/omadora/actions/runs/38461099418): installation and Omadora startup passed again. Window controls, clipboard, power profiles and Omadora logout to the KDE greeter passed; the greeter screenshot was visually inspected and rendered correctly. Plasma started and its desktop screenshot rendered correctly. Password unlock and GTK light-theme checks failed again. The Plasma logout check timed out waiting for `plasmashell` to exit; the journal shows the login greeter started, but the fixture did not capture a post-Plasma-logout screenshot. This is inconclusive for the reported black screen and is not a full pass.

## Repeat the KDE test

```bash
gh workflow run vm.yml --ref fix/kde-manual-nvidia -f edition=kde
```

The fixture uses Plasma Login Manager to start Omadora, performs desktop
interaction checks, terminates its Wayland session and captures the greeter.
It then starts Plasma and tests return to the greeter again. Autologin and
session termination are test instrumentation restricted to the disposable VM.
A running greeter process alone is not proof that the screen rendered:
inspect the saved screenshots and login-manager journal as well.

The workflow retains VM logs, per-check results and screenshots as artifacts,
including on failure. Physical GPU rendering and the G14 logout black screen
remain unvalidated by these VM results.
