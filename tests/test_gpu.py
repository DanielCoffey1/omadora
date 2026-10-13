import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import omadora_gpu as gpu


def card(vendor='NVIDIA', device='2684', pci='0000:01:00.0', driver='nvidia', boot=False):
    return dict(vendor=vendor, device=device, pci=pci, driver=driver,
                subvendor='10de', subdevice='0000', boot_display=boot)


class GPU(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'PCI sysfs names contain colons; Linux CI exercises discovery')
    def test_detection_filters_non_display_devices_and_preserves_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for index, cls, vendor in ((0, '0x030000', '0x10de'), (1, '0x040300', '0x10de'), (2, '0x030200', '0x1234')):
                p = base / f'0000:0{index}:00.0'
                p.mkdir()
                for name, value in (('class', cls), ('vendor', vendor), ('device', '0x2684'), ('boot_vga', '1')):
                    (p / name).write_text(value)
            rows = gpu.detect(base)
            self.assertEqual([r['vendor'] for r in rows], ['NVIDIA', '1234'])
            self.assertTrue(rows[0]['boot_display'])

    def test_packages_match_hardware_and_gaming_scope(self):
        amd = card('AMD', driver='amdgpu')
        self.assertIn('amd-gpu-firmware', gpu.mesa_packages([amd]))
        self.assertNotIn('intel-gpu-firmware', gpu.mesa_packages([amd]))
        self.assertFalse(any('.i686' in p for p in gpu.mesa_packages([amd])))
        self.assertIn('mesa-vulkan-drivers.i686', gpu.mesa_packages([amd], True))
        self.assertEqual(gpu.mesa_packages([card(), card('1234')]), [])
        self.assertEqual(gpu.mesa_packages([card('AMD', driver='vfio-pci')]), [])

    def test_nvidia_setup_is_rejected_before_any_operation(self):
        for dry_run in (False, True):
            a = Mock()
            with patch.object(gpu, 'detect') as detect:
                with self.assertRaisesRegex(ValueError, 'managed manually'):
                    gpu.setup(a, gaming=True, nvidia=True, dry_run=dry_run)
            detect.assert_not_called()
            a.run.assert_not_called()
            a.preflight.assert_not_called()

    def test_dry_run_does_not_install(self):
        a = Mock()
        with patch.object(gpu, 'detect', return_value=[card()]):
            gpu.setup(a, gaming=True, dry_run=True)
        a.run.assert_not_called()
        a.preflight.assert_not_called()

    def test_hybrid_setup_only_installs_mesa_and_diagnostics(self):
        a = Mock()
        cards = [card(), card('Intel', driver='i915')]
        with patch.object(gpu, 'detect', return_value=cards):
            gpu.setup(a, gaming=True)
        a.run.assert_called_once_with('sudo', 'dnf', 'install',
            *gpu.mesa_packages(cards, True), 'vulkan-tools', 'pciutils', 'mokutil')
        a.lifecycle.assert_not_called()

    def test_software_vulkan_is_not_reported_as_hardware(self):
        self.assertIn('no physical', gpu.acceleration({'status': 0, 'output': 'deviceType = PHYSICAL_DEVICE_TYPE_CPU\ndeviceName = llvmpipe'}))
        self.assertIn('hardware Vulkan', gpu.acceleration({'status': 0, 'output': 'deviceType = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU'}))
        self.assertIn('unverified', gpu.acceleration({'status': 1, 'output': ''}))

    def test_hybrid_launch_preserves_arguments_and_limits_environment(self):
        gpus = [card('Intel', pci='0000:00:02.0', driver='i915', boot=True), card()]
        with patch.object(gpu, 'detect', return_value=gpus), patch.object(gpu.os, 'execvpe') as execute:
            gpu.launch(['game', 'argument with spaces'])
        command, args, env = execute.call_args.args
        self.assertEqual(args, ['game', 'argument with spaces'])
        self.assertEqual(env['__NV_PRIME_RENDER_OFFLOAD'], '1')
        with patch.object(gpu, 'detect', return_value=[card('AMD', driver='amdgpu')]), patch.object(gpu.os, 'execvpe') as execute:
            gpu.launch(['game'])
        self.assertEqual(execute.call_args.args[2]['DRI_PRIME'], 'pci-0000_01_00_0')
        with patch.object(gpu, 'detect', return_value=gpus + [card(pci='0000:02:00.0')]):
            with self.assertRaises(ValueError):
                gpu.launch(['game'])

    def test_mux_boot_gpu_is_not_misidentified_as_integrated(self):
        cards = [card('Intel', driver='i915'), card(boot=True, pci='0000:02:00.0')]
        with patch.object(gpu, 'detect', return_value=cards), patch.object(gpu.os, 'execvpe') as execute:
            gpu.launch(['game'])
        self.assertEqual(execute.call_args.args[2]['__NV_PRIME_RENDER_OFFLOAD'], '1')
        with patch.object(gpu, 'detect', return_value=[card('AMD', driver='amdgpu'), card('Intel', driver='xe', pci='0000:02:00.0')]):
            with self.assertRaises(ValueError):
                gpu.launch(['game'])
