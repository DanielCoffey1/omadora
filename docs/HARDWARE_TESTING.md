# Physical hardware testing

The fresh Workstation ISO VM passes the desktop/recovery suite. Physical Intel,
AMD and NVIDIA GPUs, Wi-Fi, Bluetooth, multiple monitors and suspend remain
unverified. Windows and WSL cannot supply Fedora desktop/driver acceptance
results. A GPU detected in Windows is an inventory observation, not a Fedora
compatibility result.

## Collect a baseline on Fedora

Start in a local Omadora session on the physical Fedora Workstation 44 machine.
Run as your normal desktop user, without sudo. From an Omadora source checkout:

```bash
python3 tests/hardware-check.py
```

Or download the standalone collector:

```bash
curl -fL https://raw.githubusercontent.com/DanielCoffey1/omadora/main/tests/hardware-check.py -o omadora-hardware-check.py
python3 omadora-hardware-check.py
```

It writes a new `omadora-hardware-<timestamp>` folder with `report.json` and
`checklist.md`. Optional `--output DIRECTORY` chooses a new directory; an
existing directory is refused. No packages, drivers, desktop settings or
network connections are changed, and nothing is uploaded. The collector does
not trigger suspend or reboot.

The inventory records Fedora/kernel versions, detected virtualization, GPU
drivers, Secure Boot/SELinux state, available sleep modes, display configuration,
and network-device state. Missing commands and probe timeouts are recorded,
not interpreted as working hardware. Monitor serial fields and active-window
information are excluded. Review the folder before sharing it.

Every acceptance check starts as **NOT TESTED**. Running the collector is not
a pass. Put observed PASS/FAIL/NOT APPLICABLE results and details in the
checklist; the JSON remains the diagnostic baseline.

## Exercise the hardware locally

1. Test password login from GDM and again after reboot. Open Firefox and Foot;
   resize, move and fullscreen windows, and play a local video.
2. Test each display's resolution, refresh and scaling. With multiple displays,
   move windows between them, then disconnect/reconnect an external display.
   Record connector names and any flicker, corruption or lost windows.
3. Test Wi-Fi reconnect, speaker/headphone playback, microphone recording and
   Bluetooth pairing/reconnect where those devices exist. Use NOT APPLICABLE
   for absent hardware, with a reason.
4. Save your work, then use Omadora's normal lock/suspend flow at the computer.
   Wake it, verify the lock remains, unlock and recheck displays/network/audio.
   Record **three separate cycles**, including any forced restart. Do this
   locally: an SSH disconnect cannot establish successful sleep, wake or unlock.
5. Follow [maintenance and recovery](MAINTENANCE.md) from GNOME after the other
   tests. Retain the reported backup and rescue paths in your private notes.
6. Run the collector again into a new folder after testing. Keep both baselines
   and the completed checklist; note any settings or driver changes in between.

Record failures exactly and retain the working GNOME fallback while diagnosing
them. The collector does not install NVIDIA drivers or enroll Secure Boot keys.
NVIDIA setup/support remains a separate unvalidated path; a detected NVIDIA
GPU or successful `nvidia-smi` query does not establish Hyprland compatibility.

## Evidence required for a hardware result

A result needs the machine/GPU model, Fedora/kernel/driver versions, firmware
and Secure Boot state, display arrangement, completed checklist, and observed
failures. Screenshots can document rendering issues, but successful suspend and
device operation require the actual interaction observations. Do not include
passwords, Wi-Fi names or account credentials in shared notes.

For remote diagnosis, provide the Fedora machine's SSH hostname and username.
Local help is still needed for physical display connections, sound checks,
password interaction and suspend/resume. No physical machine has passed this
checklist yet.
