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

    def test_support_parser_excludes_legacy_and_respects_subsystem(self):
        html = '<a id="Current"></a><table><tr id="devid2684"><tr id="devid1E30_1028_129E"></table><table><tr id="devid1234"></table>'
        ids = gpu.supported_ids(html)
        self.assertTrue(gpu.supports(card(), ids))
        self.assertFalse(gpu.supports(card(device='1234'), ids))
        self.assertFalse(gpu.supports(card(device='1e30'), ids))
        self.assertTrue(gpu.supports(card(device='1e30') | dict(subvendor='1028', subdevice='129e'), ids))
        with self.assertRaises(ValueError):
            gpu.supported_ids('<html>Access denied</html>')

    def test_dry_run_does_not_fetch_or_install(self):
        a = Mock()
        with patch.object(gpu, 'detect', return_value=[card()]), patch.object(gpu, 'candidate') as query:
            gpu.setup(a, gaming=True, nvidia=True, dry_run=True)
        a.run.assert_not_called()
        a.preflight.assert_not_called()
        query.assert_not_called()

    def test_software_vulkan_is_not_reported_as_hardware(self):
        self.assertIn('no physical', gpu.acceleration({'status': 0, 'output': 'deviceType = PHYSICAL_DEVICE_TYPE_CPU\ndeviceName = llvmpipe'}))
        self.assertIn('hardware Vulkan', gpu.acceleration({'status': 0, 'output': 'deviceType = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU'}))
        self.assertIn('unverified', gpu.acceleration({'status': 1, 'output': ''}))

    def test_secure_boot_pending_stops_before_driver_install(self):
        a = Mock()
        a.run.return_value = subprocess.CompletedProcess([], 1, '')
        with patch.object(gpu, 'detect', return_value=[card()]), \
             patch.object(gpu, 'candidate', return_value=('', '615.71.09')), \
             patch.object(gpu, 'secure_boot', return_value='enabled'):
            self.assertEqual(gpu.setup(a, nvidia=True), 3)
        calls = [c.args for c in a.run.call_args_list]
        self.assertIn(('sudo', 'mokutil', '--import', gpu.CERT), calls)
        self.assertFalse(any(any(str(x).startswith('akmod-nvidia-') for x in c) for c in calls))
        self.assertFalse(any('dracut' in c for c in calls))

    def test_unknown_secure_boot_and_unsupported_gpu_stop(self):
        for candidate, state in ((None, 'disabled'), (('', '615.71.09'), 'unknown')):
            a = Mock()
            a.run.return_value = subprocess.CompletedProcess([], 0, '')
            with patch.object(gpu, 'detect', return_value=[card()]), \
                 patch.object(gpu, 'candidate', return_value=candidate), \
                 patch.object(gpu, 'secure_boot', return_value=state):
                with self.assertRaises(ValueError):
                    gpu.setup(a, nvidia=True)
            self.assertFalse(any('akmods' in c.args for c in a.run.call_args_list))

    def test_module_build_failure_prevents_initramfs_and_success(self):
        a = Mock()
        def run(*args, **kwargs):
            if 'akmods' in args:
                raise subprocess.CalledProcessError(1, args)
            return subprocess.CompletedProcess(args, 0, '6.19.1-1.fc44.x86_64\n' if 'kernel-devel' in args else '')
        a.run.side_effect = run
        with patch.object(gpu, 'detect', return_value=[card()]), \
             patch.object(gpu, 'candidate', return_value=('', '615.71.09')), \
             patch.object(gpu, 'secure_boot', return_value='disabled'):
            with self.assertRaises(subprocess.CalledProcessError):
                gpu.setup(a, nvidia=True)
        self.assertFalse(any('dracut' in c.args for c in a.run.call_args_list))

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
