import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, mock_open

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

    def test_supported_branch_selection_and_multilib(self):
        self.assertEqual(gpu.nvidia_branch([card(device='2684')]), 'current')
        self.assertEqual(gpu.nvidia_branch([card(device='2191')]), 'current')  # GTX 1660 Ti
        self.assertEqual(gpu.nvidia_branch([card(device='1c82')]), '580xx')  # GTX 1050 Ti
        self.assertEqual(gpu.nvidia_branch([card(device='1380')]), '580xx')  # GTX 750 Ti, not Kepler
        self.assertEqual(gpu.nvidia_branch([card(device='1c82'), card()]), '580xx')
        self.assertIsNone(gpu.nvidia_branch([card(driver='vfio-pci')]))
        for device in ('0fc0', 'ffff'):
            with self.assertRaisesRegex(ValueError, 'not in the supported'):
                gpu.nvidia_branch([card(device=device)])
        self.assertIn('xorg-x11-drv-nvidia-580xx-libs.i686', gpu.nvidia_packages('580xx'))
        self.assertNotIn('akmod-nvidia', gpu.nvidia_packages('580xx'))
        self.assertIn('xorg-x11-drv-nvidia-cuda-libs.i686', gpu.nvidia_packages('current'))
        a = Mock()
        with patch.object(gpu, 'detect', return_value=[card(device='ffff')]):
            with self.assertRaises(ValueError):
                gpu.setup(a)
        a.run.assert_not_called()

    def test_dry_run_does_not_install(self):
        a = Mock()
        with patch.object(gpu, 'detect', return_value=[card()]):
            gpu.setup(a, gaming=True, dry_run=True)
        a.run.assert_not_called()
        a.preflight.assert_not_called()

    def test_hybrid_setup_installs_both_stacks(self):
        a = Mock()
        cards = [card(), card('Intel', driver='i915')]
        with patch.object(gpu, 'detect', return_value=cards), patch.object(gpu, 'install_nvidia') as install:
            gpu.setup(a, gaming=True)
        a.run.assert_called_once_with('sudo', 'dnf', 'install', '-y',
            *gpu.mesa_packages(cards, True), 'vulkan-tools', 'pciutils', 'mokutil')
        install.assert_called_once_with(a, cards, True)
        a.lifecycle.assert_not_called()

    def adapter(self, conflict=None, version='615.71.09', module='615.71.09'):
        a = Mock()
        a.os_release.return_value = {'VERSION_ID': '44'}

        def run(*args, **kwargs):
            output, code = '', 0
            if args[:2] == ('rpm', '-q') and '--qf=%{VERSION}' not in args:
                code = 0 if args[2] == conflict else 1
            if '--default-kernel' in args:
                output = '/boot/vmlinuz-7.2.1-200.fc44.x86_64\n'
            if '--qf=%{VERSION}' in args:
                output = version
            if args[0] == 'modinfo':
                output = module if 'version' in args else 'AA:BB:CC:DD'
            if 'openssl' in args:
                output = 'serial=AABBCCDD\n'
            return subprocess.CompletedProcess(args, code, output, '')
        a.run.side_effect = run
        return a

    def test_real_setup_orders_key_build_verify_and_initramfs(self):
        a = self.adapter()
        with patch.object(gpu, 'secure_boot', return_value='enabled'), patch.object(gpu, 'enroll_key', return_value=True) as enroll:
            gpu.install_nvidia(a, [card()])
        calls = [call.args for call in a.run.call_args_list]
        self.assertLess(calls.index(('sudo', 'kmodgenca', '-a')), next(i for i, c in enumerate(calls) if 'akmod-nvidia' in c))
        self.assertIn(('sudo', 'akmods', '--force', '--rebuild', '--kernels', '7.2.1-200.fc44.x86_64'), calls)
        self.assertEqual(calls[-1], ('sudo', 'dracut', '--force', '--kver', '7.2.1-200.fc44.x86_64'))
        enroll.assert_called_once_with(a)
        self.assertFalse(any('modprobe' in c or 'systemctl' in c for c in calls))

    def test_conflict_unknown_boot_and_bad_build_stop(self):
        a = self.adapter(conflict='xorg-x11-drv-nvidia-580xx')
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            gpu.install_nvidia(a, [card()])
        self.assertFalse(any('dnf' in c.args for c in a.run.call_args_list))
        for boot, module, message in [('unknown', '615.71.09', 'Secure Boot state'), ('disabled', '580.178.04', 'version mismatch')]:
            a = self.adapter(module=module)
            with patch.object(gpu, 'secure_boot', return_value=boot):
                with self.assertRaisesRegex(ValueError, message):
                    gpu.install_nvidia(a, [card()])
            self.assertFalse(any('dracut' in c.args for c in a.run.call_args_list))

    def test_failed_build_or_wrong_signing_key_never_rebuilds_initramfs(self):
        for failure in ('akmods', 'signature'):
            a = self.adapter()
            normal = a.run.side_effect

            def run(*args, **kwargs):
                if failure == 'akmods' and 'akmods' in args and '--rebuild' in args:
                    raise subprocess.CalledProcessError(1, args)
                if failure == 'signature' and 'sig_key' in args:
                    return subprocess.CompletedProcess(args, 0, '11:22:33:44', '')
                return normal(*args, **kwargs)
            a.run.side_effect = run
            with patch.object(gpu, 'secure_boot', return_value='enabled'), patch.object(gpu, 'enroll_key', return_value=False):
                with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                    gpu.install_nvidia(a, [card()])
            self.assertFalse(any('dracut' in c.args for c in a.run.call_args_list))

    def test_enrollment_uses_tty_not_pipe_and_skips_enrolled_key(self):
        a = Mock()
        a.run.return_value.returncode = 0
        self.assertFalse(gpu.enroll_key(a))
        a.run.return_value.returncode = 1
        terminal = mock_open()
        with patch('builtins.open', terminal), patch.object(gpu.subprocess, 'run') as execute:
            self.assertTrue(gpu.enroll_key(a))
        terminal.assert_called_with('/dev/tty', 'r')
        execute.assert_called_once_with(['sudo', 'mokutil', '--import', gpu.MOK], stdin=terminal(), check=True)

    @unittest.skipIf(os.name == 'nt', 'Real pseudo-terminal verification requires Linux')
    def test_enrollment_opens_a_real_nonseekable_terminal(self):
        master, slave = os.openpty()
        real_open = open
        a = Mock()
        a.run.return_value.returncode = 1
        try:
            with patch('builtins.open', side_effect=lambda path, mode: real_open(os.ttyname(slave), mode)), patch.object(gpu.subprocess, 'run') as execute:
                execute.side_effect = lambda *args, **kwargs: self.assertTrue(kwargs['stdin'].isatty())
                self.assertTrue(gpu.enroll_key(a))
        finally:
            os.close(master)
            os.close(slave)

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
