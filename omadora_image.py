"""Offline image first-login configuration. Never downloads or runs as root."""
import json
import os
from pathlib import Path
import shutil


def initialize():
    import omadora as a
    marker = Path('/etc/omadora/image.json')
    if not marker.is_file():
        return
    if os.getuid() == 0:
        raise ValueError('Desktop initialization requires a regular user.')
    home = Path.home()
    with a.lifecycle().locked():
        complete = home / '.local/state/omadora/image-user.json'
        if complete.exists():
            return
        backup = home / '.local/state/omadora/backups' / ('image-first-login-' + a.timestamp())
        a.backup_user(home, backup)
        a.desktop_settings('save', backup)
        metadata = complete.parent / 'installation.json'
        created_metadata = False
        try:
            for name in a.CONFIGS:
                dest = home / '.config' / name
                if dest.is_symlink() or dest.is_file():
                    dest.unlink()
                elif dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(a.PREFIX / 'upstream/config' / name, dest)
            a.write(home / '.config/uwsm/env-hyprland', (a.PREFIX / 'system/omadora-env').read_text())
            fonts = home / '.local/share/fonts/omadora'
            fonts.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a.PREFIX / 'upstream/default/fonts/omarchy/omarchy.ttf', fonts / 'omarchy.ttf')
            for font in (a.PREFIX / 'assets/fonts').glob('*.ttf'):
                shutil.copy2(font, fonts / font.name)
            a.write(home / a.FONT_CONFIG, (a.PREFIX / 'system/99-omadora-fonts.conf').read_text())
            a.run('fc-cache', '-f', fonts)
            env = dict(os.environ, OMARCHY_PATH=str(a.PREFIX / 'upstream'), OMARCHY_THEME_HEADLESS='1',
                       PATH=f'{a.PREFIX}/bin:{a.PREFIX}/upstream/bin:' + os.environ['PATH'])
            a.run(a.PREFIX / 'bin/omadora', 'wallpaper', 'apply', 'Nepal_5160x2160.png', '--headless', env=env)
            a.run('Hyprland', '--verify-config', '--config', home / '.config/hypr/hyprland.lua', env=env)
            image = json.loads(marker.read_text())
            if not metadata.exists():
                a.lifecycle().atomic_json(metadata, {
                    'backup': str(backup), 'upstream': a.read_json(a.PREFIX / 'upstream.lock.json'),
                    'revision': image.get('revision') or a.lifecycle().revision(a.PREFIX),
                    'status': 'installed', 'origin': 'offline-image',
                })
                created_metadata = True
            a.lifecycle().atomic_json(complete, {'image': image, 'backup': str(backup)})
        except BaseException:
            if created_metadata:
                metadata.unlink(missing_ok=True)
            a.restore_user(home, backup)
            a.desktop_settings('restore', backup)
            raise


if __name__ == '__main__':
    initialize()
