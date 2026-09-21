import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import omadora_wallpapers as wall

ROOT = Path(__file__).resolve().parents[1]


class OfflineImage(unittest.TestCase):
    def test_bundled_original_is_used_without_network_and_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'runtime'
            assets = root / 'assets/wallpapers'
            originals = assets / 'originals'
            originals.mkdir(parents=True)
            content = b'offline-test-image'
            digest = hashlib.sha256(content).hexdigest()
            row = dict(id=digest, sha256=digest, name='image.png', size=len(content), asset=digest+'.png')
            (assets / 'catalog.json').write_text(json.dumps(dict(images=[row])))
            image = originals / digest
            image.write_bytes(content)
            lib = wall.Library(Path(tmp) / 'home', root)
            with patch.object(wall, 'urlopen', side_effect=AssertionError('Network used')):
                self.assertEqual(lib.file(row), image)
                image.write_bytes(b'corruption')
                with self.assertRaisesRegex(ValueError, 'damaged'):
                    lib.file(row)

    def test_public_installer_requires_interactive_storage_and_account(self):
        text = (ROOT / 'iso/installer.ks.in').read_text()
        before_post = text.split('%post')[0]
        for command in ('clearpart', 'autopart', 'part ', 'ignoredisk', 'zerombr', 'user ', 'reboot'):
            self.assertFalse(any(line.startswith(command) for line in before_post.splitlines()), command)
        self.assertIn('rootpw --lock', before_post)
        self.assertIn('--checksum=@PAYLOAD_SHA256@', before_post)
        self.assertIn('if not users:', text)
        self.assertNotIn('NOPASSWD', text)
        self.assertNotIn('AutomaticLoginEnable', text)


if __name__ == '__main__':
    unittest.main()
