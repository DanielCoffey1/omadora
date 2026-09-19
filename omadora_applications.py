"""Fresh desktop-entry snapshots and best-effort notification of the live shell."""
import json
import os
from pathlib import Path
import subprocess


def refresh():
    # Installation/removal must retain its own result if no shell is running.
    try:
        subprocess.run(['omarchy-shell', '-q', 'omadora.apps', 'refresh'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def snapshot():
    # Include exports even when Flatpak was first used after this session began.
    dirs = os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share'
    extra = [str(Path.home() / '.local/share/flatpak/exports/share'),
             '/var/lib/flatpak/exports/share']
    os.environ['XDG_DATA_DIRS'] = ':'.join(dict.fromkeys([*dirs.split(':'), *extra]))
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio
    entries = []
    for app in Gio.AppInfo.get_all():
        if not app.should_show() or not app.get_id():
            continue
        icon = app.get_string('Icon') or ''
        entries.append({'id': app.get_id().removesuffix('.desktop'),
                        'name': app.get_display_name(),
                        'genericName': app.get_generic_name() or '',
                        'comment': app.get_description() or '',
                        'keywords': list(app.get_keywords() or []), 'icon': icon})
    return entries


if __name__ == '__main__':
    print(json.dumps(snapshot()))
