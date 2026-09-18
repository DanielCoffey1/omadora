"""Do not confuse diagnostic availability with physical hardware acceptance."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hardware_check', Path(__file__).with_name('hardware-check.py'))
hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hardware)


class HardwareTests(unittest.TestCase):
    def test_missing_or_failed_virtualization_probe_is_not_physical_evidence(self):
        for result in ({'status': 'unavailable'}, {'status': 'timeout'},
                       {'status': 'error', 'returncode': 1, 'stdout': ''}):
            self.assertEqual(hardware.classify_virtualization(result), 'unknown')
        self.assertEqual(hardware.classify_virtualization({'status': 'ok', 'stdout': 'kvm'}), 'virtualized')
        self.assertEqual(hardware.classify_virtualization({'returncode': 1, 'stdout': 'none'}), 'no_virtualization_detected')

    def test_monitor_inventory_excludes_serial_and_window_information(self):
        with patch.object(hardware, 'probe', return_value={'status': 'ok', 'stdout':
             '[{"name":"DP-1","width":2560,"serial":"private","description":"serial embedded","activeWorkspace":{"name":"private"}}]'}):
            self.assertEqual(hardware.monitor_probe(), {'status': 'ok', 'monitors': [{'name': 'DP-1', 'width': 2560}]})
        with patch.object(hardware, 'probe', return_value={'status': 'ok', 'stdout': '{}'}):
            self.assertEqual(hardware.monitor_probe(), {'status': 'invalid_json'})

    def test_probe_handles_missing_command_and_timeout(self):
        with patch.object(hardware.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertEqual(hardware.probe(['missing']), {'status': 'unavailable'})
        with patch.object(hardware.subprocess, 'run', side_effect=subprocess.TimeoutExpired('probe', 15)):
            self.assertEqual(hardware.probe(['probe']), {'status': 'timeout'})

    def test_collection_never_claims_manual_checks_passed(self):
        with patch.object(hardware, 'probe', return_value={'status': 'ok', 'stdout': 'kvm'}), \
             patch.object(hardware, 'monitor_probe', return_value={'status': 'ok', 'monitors': []}), \
             patch.object(hardware, 'read_value', return_value=None):
            report = hardware.collect()
        self.assertEqual(report['environment'], 'virtualized')
        self.assertTrue(all(item['status'] == 'not_tested' for item in report['manual_checks'].values()))
