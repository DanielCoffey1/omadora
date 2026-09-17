import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omadora_deploy import Deployment, atomic_json


@unittest.skipIf(os.name == 'nt', 'Real deployment symlinks exercised in Linux CI')
class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.d = Deployment(self.base / 'root')
        self.stage = self.base / 'stage'
        for name in ('omadora.py', 'omadora_deploy.py', 'omadora_lifecycle.py',
                     'bin/omadora', 'bin/omadora-session', 'system/omadora.desktop',
                     'system/omarchy-lock-password'):
            path = self.stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('new')

    def test_install_recovery_removes_only_new_files(self):
        unrelated = self.d.prefix.parent / 'other-project'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('keep')
        self.d.begin('one', 1000)
        self.d.deploy('one', 1000, self.stage)
        self.assertFalse(self.d.paths[-1].exists(), 'Do not publish login before validation')
        self.d.activate('one', 1000)
        self.d.rollback('one', 1000)
        self.assertTrue(all(not os.path.lexists(p) for p in self.d.paths))
        self.assertEqual(unrelated.read_text(), 'keep')

    def seed_old(self):
        self.d.prefix.mkdir(parents=True)
        (self.d.prefix / 'old').write_text('previous desktop')
        for path in self.d.paths[1:]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('previous entrypoint')

    def assert_old(self):
        self.assertEqual((self.d.prefix / 'old').read_text(), 'previous desktop')
        self.assertFalse((self.d.prefix / 'omadora.py').exists())
        for path in self.d.paths[1:]:
            self.assertEqual(path.read_text(), 'previous entrypoint')

    def test_upgrade_rollback_restores_all_entrypoints(self):
        self.seed_old()
        self.d.begin('one', 1000)
        self.d.deploy('one', 1000, self.stage)
        self.d.activate('one', 1000)
        self.d.rollback('one', 1000)
        self.assert_old()

    def test_interruption_between_directory_renames_is_recoverable(self):
        self.seed_old()
        self.d.begin('one', 1000)
        replace = os.replace
        def interrupt(source, destination):
            if Path(source).name == '.omadora-staged':
                raise KeyboardInterrupt()
            replace(source, destination)
        with patch('omadora_deploy.os.replace', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.d.deploy('one', 1000, self.stage)
        self.assertFalse(self.d.prefix.exists())
        self.d.rollback('one', 1000)
        self.assert_old()

    def test_interrupted_recovery_can_be_repeated(self):
        self.seed_old()
        self.d.begin('one', 1000)
        self.d.deploy('one', 1000, self.stage)
        replace = os.replace
        def interrupt(source, destination):
            if Path(destination) == self.d.paths[2]:
                raise KeyboardInterrupt()
            replace(source, destination)
        with patch('omadora_deploy.os.replace', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.d.rollback('one', 1000)
        self.d.rollback('one', 1000)
        self.assert_old()

    def test_concurrent_and_wrong_owner_operations_refused(self):
        self.d.begin('one', 1000)
        with self.assertRaises(ValueError):
            self.d.begin('two', 1001)
        for token, uid in (('wrong', 1000), ('one', 1001)):
            with self.assertRaises(ValueError):
                self.d.rollback(token, uid)
        self.d.rollback('one', 1000)

    def test_incomplete_backup_refused_before_removing_current(self):
        self.seed_old()
        self.d.begin('one', 1000)
        self.d.deploy('one', 1000, self.stage)
        (self.d.state / 'backup/1').unlink()
        with self.assertRaises(ValueError):
            self.d.rollback('one', 1000)
        self.assertEqual((self.d.prefix / 'omadora.py').read_text(), 'new')

    def test_commit_retains_candidate_and_cleans_snapshot(self):
        self.d.begin('one', 1000)
        self.d.deploy('one', 1000, self.stage)
        self.d.activate('one', 1000)
        self.d.finish('one', 1000)
        self.assertEqual((self.d.prefix / 'omadora.py').read_text(), 'new')
        self.assertIsNone(self.d.status())

    def test_preparation_interruption_does_not_remove_old_desktop(self):
        self.seed_old()
        self.d.state.mkdir(parents=True)
        atomic_json(self.d.journal, {'token': 'one', 'uid': 1000, 'phase': 'preparing', 'existed': []})
        self.d.rollback('one', 1000)
        self.assert_old()

    def test_successful_upgrade_can_return_to_previous_desktop(self):
        self.seed_old()
        self.d.begin('one', 1000)
        self.d.deploy('one', 1000, self.stage)
        self.d.activate('one', 1000)
        self.d.finish('one', 1000)
        self.d.begin('two', 1000)
        self.d.revert('two', 1000)
        self.assert_old()
        # If validation of the old desktop fails, recovery returns to the new.
        self.d.rollback('two', 1000)
        self.assertEqual((self.d.prefix / 'omadora.py').read_text(), 'new')
