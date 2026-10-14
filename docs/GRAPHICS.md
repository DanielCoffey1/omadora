# Graphics and gaming setup

Omadora targets Fedora Workstation or KDE Plasma Desktop 44, x86_64. Fresh
installation and upgrade detect PCI display controllers and active drivers.
Unknown/virtual devices and GPUs assigned to `vfio-pci` are left alone.

## Automatic driver setup

AMD/Intel hardware receives Fedora's Mesa/OpenGL/Vulkan libraries and matching
firmware, including 32-bit libraries for native Steam/Wine. Fedora supplies the
kernel drivers.

For supported NVIDIA display GPUs, the same one-command installer:

1. Selects **current** for Turing and newer, or **580xx** for supported Maxwell,
   Pascal and Volta devices, using checked-in NVIDIA PCI tables rather than
   product-name guesses. Multiple NVIDIA cards must share a supported branch.
2. Enables RPM Fusion free/nonfree and installs the selected `akmod-nvidia`
   package, driver tools (`nvidia-smi`), firmware and power-management package.
3. Installs matching 32-bit NVIDIA OpenGL/Vulkan/CUDA libraries, Vulkan loader,
   GameMode and MangoHud. This provides driver libraries used by games; it does
   not install a CUDA development toolkit or automatically enable overlays.
4. Creates/reuses the akmods signing key. With Secure Boot enabled, checks whether
   it is enrolled and requests enrollment when needed.
5. Installs matching kernel headers, builds the NVIDIA module for the next-boot
   default kernel, checks its version against userspace, verifies the signing-key
   identity, and regenerates that kernel's initramfs.

The installer waits for the build rather than telling you to reboot while akmods
is still compiling. A failed build or version/signature mismatch stops setup;
inspect `/var/cache/akmods/` and retry after resolving the reported error.
**Reboot after successful setup.** The active graphics driver is not unloaded
and your current desktop is not stopped.

RPM Fusion owns the Nouveau/Nova blacklists, DRM defaults and suspend services.
Omadora does not write an `xorg.conf`, force a dedicated GPU as the desktop GPU,
or apply upstream's global NVIDIA environment overrides. Steam, Lutris, Heroic,
Bottles and other launchers remain available through the app menu.

470xx/390xx and unknown PCI IDs are not automatically installed: those devices
are outside this Hyprland desktop's supported driver set. An existing conflicting
RPM driver branch or NVIDIA `.run` installation stops with an explanation rather
than being erased. Matching RPM Fusion installations can be updated by setup.
GPU branch membership is generated with `python3 tools/update-nvidia-ids.py`;
the source URLs and hashes are recorded in `assets/nvidia-pci.json`.

## Secure Boot

Secure Boot is kept enabled. If the akmods certificate is not already enrolled,
`mokutil` asks for a temporary password in the terminal, including when installation
starts with `curl | bash`. The password is not put in arguments or logs.
On reboot, select **Enroll MOK**, **Continue**, **Yes**, enter that password, and
reboot again if requested. Firmware confirmation cannot be automated by the
installer. The driver cannot load until enrollment succeeds; a prepared build
with pending enrollment is explicitly reported. An unknown Secure Boot state
stops NVIDIA setup.

## Status and existing installations

The README's one-command **upgrade** runs the same automatic GPU setup. You can
also open **Install > Gaming > GPU setup** or run:

```bash
omadora gpu setup --gaming --dry-run
omadora gpu setup --gaming
omadora gpu status
omadora gpu status --json
```

Automatic provisioning runs in the Fedora bootstrap installer and upgrade.
The separate offline ISO does not bundle RPM Fusion drivers; use the fresh
Fedora plus one-command route for automatic NVIDIA setup before first login.

`--nvidia` remains accepted, but detection is now automatic and that flag will not
install a driver on a machine without a supported NVIDIA display GPU.
Status reports PCI identity, active driver, Secure Boot, Vulkan devices and NVIDIA
DRM modesetting. CPU/llvmpipe is not reported as hardware acceleration.

Flatpak applications use their own driver runtime extensions. After rebooting
into a new NVIDIA driver, update installed Flatpak applications with
`flatpak update --user` (and `flatpak update` for system-installed applications)
so their NVIDIA extensions match. Host multilib packages do not replace them.
Desktop rollback/recovery does not undo system RPMs, initramfs or MOK enrollment.

## Hybrid laptops and per-game GPU selection

Keep the desktop on its normal GPU. Run a new process on a selected GPU:

```bash
omadora gpu run -- game-command
omadora gpu run --pci 0000:01:00.0 -- game-command
```

Use an address from GPU status. A single NVIDIA card is selected by default,
or the only GPU on a single-GPU system. Multiple Mesa GPUs require an explicit
PCI address; boot-display flags do not identify discrete graphics on MUX laptops.
Mesa uses `DRI_PRIME`; a single NVIDIA offload device uses NVIDIA's PRIME variables.
Multiple NVIDIA offload devices require manual provider setup. An already-running
application cannot have its GPU changed by this wrapper.

For a native Steam game's **Launch Options**:

```text
omadora gpu run -- %command%
```

Flatpak sandbox access to host commands is separate; the wrapper is not assumed
to be available inside a sandbox.

## Sources and test boundaries

On October 14, 2026, the [GPU matrix](https://github.com/DanielCoffey1/omadora/actions/runs/38639430505)
passed for Mesa, NVIDIA 615.78.08 (open) and NVIDIA 580.178.04 (proprietary),
including signed module builds and both gaming-helper architectures. The
[validation record](VM_ACCEPTANCE.md#automatic-nvidia-update--october-14-2026)
also records 92 Linux source checks and passing KDE/Workstation VM regressions.

- [RPM Fusion driver packaging](https://github.com/rpmfusion/xorg-x11-drv-nvidia)
- [RPM Fusion 580xx packaging](https://github.com/rpmfusion/xorg-x11-drv-nvidia-580xx)
- [RPM Fusion module selection and builds](https://github.com/rpmfusion/nvidia-kmod)
- [RPM Fusion Secure Boot instructions](https://rpmfusion.org/Howto/Secure%20Boot)
- [NVIDIA current/legacy PCI tables](https://download.nvidia.com/XFree86/Linux-x86_64/615.71.09/README/supportedchips.html)
- [NVIDIA 580 supported devices](https://download.nvidia.com/XFree86/Linux-x86_64/580.178.04/README/supportedchips.html)
- [NVIDIA PRIME offload](https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/primerenderoffload.html)
- [Mesa DRI_PRIME](https://docs.mesa3d.org/envvars.html#envvar-DRI_PRIME)

Unit checks cover PCI layouts, current/580xx selection, unknown/passthrough GPUs,
conflicting drivers, Secure Boot gates and terminal enrollment, failed builds,
module version/signature checks, dry runs and per-process offload. The GPU workflow
installs actual Fedora/RPM Fusion packages and builds signed NVIDIA modules for
a real Fedora kernel in disposable containers. The containers substitute PCI
identity and next-boot kernel selection, and do not emulate firmware enrollment.
The 580xx fixture disables the builder's host-PCI detection only inside the
disposable container to exercise the proprietary module required by Pascal;
the current fixture checks the open module. Real installation leaves RPM Fusion's
hardware-based module selection intact.
VM desktop tests exercise virtual display hardware; neither establishes physical
NVIDIA rendering, laptop suspend or game performance. Missing drivers alone do
not establish the cause of an existing black screen.
