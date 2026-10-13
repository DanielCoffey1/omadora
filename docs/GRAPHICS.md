# Graphics and gaming setup

Omadora targets Fedora Workstation or KDE Plasma Desktop 44, x86_64. Graphics setup does not install
games or a CUDA development toolkit, change the theme, disable Secure Boot,
unload a running driver, or force the whole desktop onto a dedicated GPU.

## Fresh installations

The installer reads PCI display controllers and active kernel drivers. For
AMD/Intel graphics it ensures Fedora's 64-bit Mesa/OpenGL/Vulkan stack and
the matching vendor firmware package are present. Fedora supplies the kernel
drivers; Omadora does not install AMD's proprietary stack. Unknown/virtual
devices and GPUs bound to vfio-pci are left alone.

NVIDIA detection prints a reminder to manage drivers manually after installation.
No NVIDIA driver or firmware enrollment changes are performed.

## Existing installations and gaming libraries

Open **Setup → Graphics** for status or AMD/Intel gaming libraries.
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
users manage matching 32-bit libraries themselves with their driver installation.

Status reports PCI identity, active driver, Secure Boot state, Vulkan devices
and NVIDIA DRM modesetting. CPU/llvmpipe Vulkan is not reported as hardware
acceleration. Detection is not a gameplay or suspend certification.

## NVIDIA

Install or update NVIDIA drivers yourself after Omadora installation, from
GNOME, Plasma or a TTY. Reboot before checking `omadora gpu status` and logging
into Omadora. The default Fedora driver remains in use until you change it;
Omadora does not guarantee that it can run Hyprland on every NVIDIA GPU.

Omadora does not enable driver repositories, select a driver branch, install
NVIDIA packages, build kernel modules, rebuild the initramfs for NVIDIA, or
import Secure Boot keys. NVIDIA gaming libraries are also managed manually.
The former `omadora gpu setup --nvidia` command now stops with an explanation
before making any changes. Existing driver installations are left in place.
The desktop also skips upstream NVIDIA environment overrides; any hardware
specific Hyprland settings are yours to configure.

## Hybrid laptops and per-game GPU selection

Keep the desktop on its normal GPU. Run a new process on the selected GPU:

```bash
omadora gpu run -- game-command
omadora gpu run --pci 0000:01:00.0 -- game-command
```

Use an address reported by GPU status. A single NVIDIA card is selected by
default, or the only GPU on a single-GPU system. Multiple Mesa GPUs require an
explicit PCI address: boot-display flags do not reliably identify discrete
graphics on MUX laptops. Mesa uses `DRI_PRIME`; a single NVIDIA
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

Tests cover simulated PCI layouts, refusal of the former NVIDIA install path,
Mesa package selection and per-process environment selection. The Fedora GPU
container workflow installs Mesa packages and verifies that NVIDIA setup does
not install driver packages or enable RPM Fusion. Containers cannot establish
physical GPU rendering, laptop power management or game performance.
