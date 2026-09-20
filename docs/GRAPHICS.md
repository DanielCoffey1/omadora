# Graphics and gaming setup

Omadora targets Fedora Workstation 44, x86_64. Graphics setup does not install
games or a CUDA development toolkit, change the theme, disable Secure Boot,
unload a running driver, or force the whole desktop onto a dedicated GPU.

## Fresh installations

The installer reads PCI display controllers and active kernel drivers. For
AMD/Intel graphics it ensures Fedora's 64-bit Mesa/OpenGL/Vulkan stack and
the matching vendor firmware package are present. Fedora supplies the kernel
drivers; Omadora does not install AMD's proprietary stack. Unknown/virtual
devices and GPUs bound to vfio-pci are left alone.

NVIDIA detection prints the next command to run from GNOME before starting
Omadora. NVIDIA replacement is a separate explicit setup operation because
driver compatibility and firmware enrollment need checking.

## Existing installations and gaming libraries

Open **Setup → Graphics** for status, gaming libraries or NVIDIA driver setup.
The **Install → Gaming → GPU setup** entry installs the optional gaming
graphics libraries and explains the NVIDIA path if needed.

```bash
omadora gpu status
omadora gpu status --json
omadora gpu setup --gaming --dry-run
omadora gpu setup --gaming
```

AMD/Intel gaming setup adds 32-bit Mesa/OpenGL/Vulkan libraries for native
Steam/Wine workloads. Flatpak apps also manage their own runtime extensions;
these host packages do not substitute for Flatpak runtime updates. NVIDIA
users should use the driver setup below to install matching 32-bit libraries.

Status reports PCI identity, active driver, Secure Boot state, Vulkan devices
and NVIDIA DRM modesetting. CPU/llvmpipe Vulkan is not reported as hardware
acceleration. Detection is not a gameplay or suspend certification.

## NVIDIA

Log out of Hyprland and use GNOME or a TTY as your normal user:

```bash
omadora gpu setup --nvidia --gaming
```

The tool enables Fedora 44 RPM Fusion free/nonfree repositories, queries the
available current driver and checks NVIDIA's PCI support table for that exact
version. If necessary it tries RPM Fusion's 580xx branch. All NVIDIA display
controllers must fit one verified branch; unsupported/older or incompatible
mixed cards stop with an explanation. It does not guess support from marketing
names. Existing alternate driver branches/providers or .run installs require
manual migration; they are not silently removed.

With Secure Boot enabled, Omadora uses akmods' existing key-generation tools.
If its certificate is not enrolled, it requests MOK enrollment and stops before
installing the NVIDIA driver (exit status 3). Choose an enrollment password,
reboot, select **Enroll MOK → Continue → Yes**, and enter that password.
Then rerun the setup command from GNOME/TTY. Firmware approval remains a human
step; Omadora never disables Secure Boot or enrolls a key on your behalf.

After enrollment (or with Secure Boot disabled), setup installs the verified
driver version and matching libraries, including NVIDIA's diagnostic tools
(`nvidia-smi`, supplied in the RPM named `xorg-x11-drv-nvidia[-580xx]-cuda`).
That package is not the CUDA compiler/toolkit. RPM Fusion chooses the open or
closed kernel module suitable for its supported hardware. Setup ensures
matching Fedora kernel headers, explicitly builds the akmod, verifies module
presence/signing where required, and regenerates initramfs. It does not reboot
automatically. A build failure stops the flow; review its output before reboot.

Reboot after successful setup and run `omadora gpu status` in the desktop.
DNF updates maintain RPM Fusion packages/akmods. Secure Boot, kernel updates,
external displays and suspend still require physical-hardware testing.

Driver/repository/kernel changes are not undone by `omadora rollback`, which
only restores the previous desktop deployment. Use Fedora package recovery or
a previously working kernel for driver problems; GNOME remains available.

## Hybrid laptops and per-game GPU selection

Keep the desktop on its normal GPU. Run a new process on the non-boot GPU:

```bash
omadora gpu run -- game-command
omadora gpu run --pci 0000:01:00.0 -- game-command
```

Use an address reported by GPU status. When selection is ambiguous the tool
asks for an explicit PCI address. Mesa uses `DRI_PRIME`; a single NVIDIA
offload device uses NVIDIA's PRIME variables. Multiple NVIDIA offload devices
require manual provider setup. No commands are passed through a shell by
Omadora. An already-running app cannot have its GPU changed by this command.

For a Steam game's **Launch Options**, use:

```text
omadora gpu run -- %command%
```

This applies to native Steam. Flatpak sandbox access to host commands is a
separate concern; do not assume this host wrapper is available inside it.

## Sources and test boundaries

- [Fedora firmware packages](https://packages.fedoraproject.org/pkgs/linux-firmware/)
- [RPM Fusion NVIDIA packaging](https://github.com/rpmfusion/xorg-x11-drv-nvidia)
- [RPM Fusion akmod packaging and module selection](https://github.com/rpmfusion/nvidia-kmod)
- [NVIDIA supported GPU tables](https://download.nvidia.com/XFree86/Linux-x86_64/615.71.09/README/supportedchips.html)
- [NVIDIA PRIME offload](https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/primerenderoffload.html)
- [Mesa DRI_PRIME](https://docs.mesa3d.org/envvars.html#envvar-DRI_PRIME)

Tests cover simulated PCI layouts, branch matching, failure handling, Secure
Boot gating and per-process environment selection. Fedora containers exercise
real packages and NVIDIA module builds. PCI IDs and firmware trust are simulated
in those containers, and initramfs is generated without a host-only root device.
Neither those tests nor a successful module build prove physical GPU rendering,
firmware enrollment, laptop power management or game performance.
