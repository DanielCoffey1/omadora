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

The app-validation workflow retains virtio graphics so this known failure remains visible. The suspend-diagnostic workflow defaults to the verified Bochs profile and retains the alternative profiles for investigation. Changing the VM's display device happens on the host; the Fedora installer does not change it automatically. Physical GPU suspend remains untested.

## GDM startup fix

Omadora now uses Hyprland's packaged startup entry and activates the authenticated local GDM session through logind before starting UWSM. This addresses the recorded inactive-session timeout. Twenty subsequent GDM relaunches across four VMs passed password checks, including five deliberately delayed launches. The installer does not enable autologin; autologin exists only in the disposable test fixture.
