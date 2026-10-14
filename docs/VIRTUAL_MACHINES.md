# Virtual machine testing

## Tested suspend configuration

For QEMU suspend testing, use a **single Bochs display with software rendering**. Replace the existing video/display arguments with:

```bash
-vga none -device bochs-display -display gtk,gl=off
```

`-vga none` is necessary: without it, QEMU adds its default VGA alongside the Bochs device, which caused renderer failures in the first control test. Keep your existing disk, memory, CPU, networking and other VM arguments.

The [verified run](https://github.com/DanielCoffey1/omadora/actions/runs/35257282229) passed five GDM relaunches with real password checks and three consecutive ACPI S3 suspend/resume cycles. Each cycle retained the secure lock, accepted the correct password after wake, and returned to the desktop. The final desktop capture was inspected. This used QEMU 8.2.2, Fedora 44, kernel 7.2.5 and Hyprland 0.56.2 with the normal Omadora lock and sleep code.

To reproduce the disposable CI test, select `bochs-gpu` in the **Fedora suspend diagnostic** workflow, or run:

```bash
gh workflow run diagnostic.yml -R DanielCoffey1/omadora -f mode=bochs-gpu
```

This is a verified VM workaround, not a repair to the virtio driver. Software graphics are intended for desktop and suspend validation; hardware acceleration and gaming performance are not established by this run. The fixture installs Workstation packages on the official Fedora Cloud image, rather than installing from the Workstation ISO.

## Remaining virtio limitation

The original virtio/virgl configuration still hangs after S3 with Hyprland blocked in the kernel's `drm_atomic_helper_swap_state`. Turning off 3D acceleration passed one cycle but failed the second. Blanking the display before sleep and the earlier legacy-DRM experiment also failed. These workarounds are not enabled in Omadora.

The graphical and catalog workflows now use the verified Bochs profile by
default. The suspend-diagnostic workflow retains the explicit virtio/GL profiles
for investigation. Changing the VM's display device happens on the host; the
Fedora installer does not change it automatically. Physical GPU suspend remains
untested.

Zed's VM probe explicitly opts into software rendering with
`flatpak run --env=ZED_ALLOW_EMULATED_GPU=1 dev.zed.Zed`; this test option is not
written to the user's launcher. Zed otherwise asks the user to acknowledge its
software-GPU warning. Native GeForce NOW requires Vulkan video decoding, which
this software display cannot provide. Its install/removal checks are separate
from application readiness. See [NVIDIA's launch troubleshooting](https://nvidia.custhelp.com/app/answers/detail/a_id/5737/kw/DYNAMIC).

## GDM startup fix

Omadora uses Hyprland's packaged startup entry and activates the authenticated
local session through logind before starting UWSM. It first waits for a queued
`graphical.target` boot job to finish: activating earlier allowed GDM to take
the VT back while UWSM waited for boot, causing Aquamarine's inactive-session
timeout. The wait is bounded and a failure stops compositor startup with an
explanation. It does not activate a remote or seatless session. The installer
does not enable autologin; autologin exists only in the disposable test fixture.
