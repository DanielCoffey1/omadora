#!/usr/bin/python3
"""Omadora's Fedora adapter. Python standard library only; no shell eval."""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
VERSION = '0.1.0-alpha'
RELEASE_REF = 'v' + VERSION
PREFIX = Path('/usr/local/share/omadora')
COPR = 'nett00n/hyprland'
SCREENSAVER_COPR = 'whelanh/omarchy'
CONFIGS = ('hypr', 'foot', 'omarchy')
FONT_CONFIG = '.config/fontconfig/conf.d/99-omadora.conf'
DESKTOP_KEYS = ('color-scheme', 'gtk-theme', 'icon-theme')
DISALLOWED = re.compile(r'\b(pacman|yay|paru|mkinitcpio|limine|arch-chroot|pacstrap|ufw)\b')
UNPORTED = ('omarchy-install-', 'omarchy-setup-', 'omarchy-provision-',
            'omarchy-apply-', 'omarchy-dev-', 'omarchy-update-',
            'omarchy-snapshot-', 'omarchy-migrate', 'omarchy-reinstall-',
            'omarchy-refresh-', 'omarchy-pkg-', 'omarchy-theme-set-browser')


def run(*argv, capture=False, check=True, env=None):
    result = subprocess.run([str(a) for a in argv], check=False, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, env=env)
    if check and result.returncode:
        if capture:
            print(result.stdout or '', end='', file=sys.stderr)
            print(result.stderr or '', end='', file=sys.stderr)
        result.check_returncode()
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, content, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')
    if mode is not None:
        path.chmod(mode)


def packages():
    return [s for line in (ROOT / 'packages/core.txt').read_text().splitlines()
            if (s := line.split('#')[0].strip())]


def os_release(path='/etc/os-release'):
    result = {}
    for line in Path(path).read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            result[key] = value.strip('"\'')
    return result


def validate_target(info, machine, atomic=False):
    if info.get('ID') != 'fedora' or info.get('VARIANT_ID') != 'workstation':
        raise ValueError('This release targets Fedora Workstation, not another edition.')
    if info.get('VERSION_ID') != '44' or machine != 'x86_64' or atomic:
        raise ValueError('Target: Fedora Workstation 44, x86_64, non-Atomic.')


def preflight():
    if os.name != 'posix' or not hasattr(os, 'geteuid') or os.geteuid() == 0:
        raise ValueError('Run as a regular Fedora user. Omadora invokes sudo when needed.')
    validate_target(os_release(), platform.machine(), Path('/run/ostree-booted').exists())


def load_menu(path):
    # Pinned upstream stores one complete entry per line; parse entries without
    # stripping // inside URL strings. Fail if upstream changes this format.
    result = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('//') or line in ('{', '}'):
            continue
        result.update(json.loads('{' + line.rstrip(',') + '}'))
    if 'install' not in result or 'system.lock' not in result:
        raise ValueError('Unexpected upstream menu format')
    return result


def app_commands(app, action, fedora='44'):
    if action not in ('install', 'remove'):
        raise ValueError('Invalid app action')
    if app['source'] == 'optional':
        return [['python3', str(ROOT / 'omadora_optional.py'), action, app['recipe']]]
    if app['source'] == 'flatpak':
        commands = []
        if action == 'install':
            commands.append(['flatpak', 'remote-add', '--user', '--if-not-exists',
                             app.get('remote', 'flathub'), app.get('remote_url', 'https://flathub.org/repo/flathub.flatpakrepo')])
        commands.append(['flatpak', 'install' if action == 'install' else 'uninstall',
                         '--user', *([app.get('remote', 'flathub')] if action == 'install' else []), app['id']])
        return commands
    commands = []
    if app['source'] == 'vendor' and action == 'install':
        for url in (app.get('repo', app['key']), app['key']):
            if not re.fullmatch(r'https://[A-Za-z0-9./_-]+', url):
                raise ValueError('Invalid vendor repository URL')
        commands.append(['sudo', 'rpm', '--import', app['key']])
        if app.get('repo_file'):
            if not re.fullmatch('[a-z0-9-]+\\.repo', app['repo_file']):
                raise ValueError('Invalid repository filename')
            commands.append(['sudo', 'install', '-m644', str(ROOT / 'assets/repos' / app['repo_file']),
                             '/etc/yum.repos.d/omadora-' + app['repo_file']])
        else:
            commands.append(['sudo', 'dnf', 'config-manager', 'addrepo', '--overwrite',
                             '--from-repofile=' + app['repo']])
    if app['source'] == 'copr' and action == 'install':
        if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', app['copr']):
            raise ValueError('Invalid COPR repository')
        commands.append(['sudo', 'dnf', 'copr', 'enable', app['copr']])
    if app['source'] == 'rpmfusion' and action == 'install':
        for kind in ('free', 'nonfree'):
            commands.append(['sudo', 'dnf', 'install',
                             f'https://mirrors.rpmfusion.org/{kind}/fedora/rpmfusion-{kind}-release-{fedora}.noarch.rpm'])
    commands.append(['sudo', 'dnf', action, *app['packages']])
    return commands


def menu_for_fedora(menu, apps, blocked):
    result = {}
    for key, value in menu.items():
        if key.split('.')[0] in ('install', 'remove', 'update', 'setup'):
            continue
        if key in ('learn.arch', 'learn.community', 'learn.herdr-keybindings',
                   'learn.tmux-keybindings', 'trigger.hardware.hybrid-gpu',
                   'trigger.toggle.crash-capture'):
            continue
        commands = ' '.join(str(value.get(k, '')) for k in ('action', 'when', 'disabled', 'checked'))
        if DISALLOWED.search(commands) or any(name in commands for name in blocked):
            continue
        if key.startswith(('trigger.transcode', 'trigger.share',
                           'trigger.capture.screenrecord', 'trigger.capture.text',
                           'trigger.capture.qr', 'style.about')):
            continue
        result[key] = value
        # The shell evaluates checkmarks independently of visibility. Keep a
        # hidden hardware item's checkmark from invoking an absent utility.
        if value.get('when') and value.get('checked'):
            result[key] = value | {'checked': f"{{ {value['when']}; }} && {{ {value['checked']}; }}"}
    result['about'] = {'label': 'About Omadora', 'icon': '', 'action': 'foot --hold omadora about'}
    if 'learn.omarchy' in result:
        result['learn.omarchy']['action'] = 'xdg-open https://github.com/DanielCoffey1/omadora#readme'
    if 'learn.neovim' in result:
        result['learn.neovim']['action'] = 'xdg-open https://neovim.io/doc/user/'
    if 'trigger.capture' in result:
        result['trigger.capture']['aliases'] = ['capture', 'screenshot', 'recording']
    result['learn.fedora'] = {'label': 'Fedora', 'icon': '', 'action': 'xdg-open https://docs.fedoraproject.org/'}
    result['setup'] = {'label': 'Setup', 'icon': ''}
    for key, label, action in (
        ('network', 'Network', 'omarchy-shell shell toggle omarchy.network'),
        ('audio', 'Audio', 'omarchy-shell shell toggle omarchy.audio'),
        ('config', 'Hyprland configuration', 'foot nvim ~/.config/hypr/hyprland.lua'),
    ):
        if not any(name in action for name in blocked):
            result[f'setup.{key}'] = {'label': label, 'action': action}
    for action, label in (('install', 'Install'), ('remove', 'Remove')):
        result[action] = {'label': label, 'icon': '󰉉'}
        # Retain portable upstream workflows, independently of optional apps.
        for suffix in ('webapp', 'style', 'style.theme', 'style.background'):
            key = f'{action}.{suffix}'
            if key in menu:
                entry = dict(menu[key])
                if key == 'remove.webapp':
                    entry['when'] = 'test -n "$(grep -sl \'^Exec=omarchy-launch-webapp \' "$HOME"/.local/share/applications/*.desktop 2>/dev/null)"'
                command = entry.get('action', '')
                if not DISALLOWED.search(command) and not any(name in command for name in blocked):
                    entry['action'] = command.replace('omarchy-launch-floating-terminal-with-presentation', 'foot --hold') if command else ''
                    if not command:
                        entry.pop('action')
                    result[key] = entry
        result[f'{action}.package'] = {'label': 'Fedora package', 'icon': '', 'action': f'foot omadora-terminal-action omadora package {action}'}
        for app_id, app in apps.items():
            category = '.'.join(filter(None, (action, app['category'])))
            parts = app['category'].split('.') if app['category'] else []
            for index, part in enumerate(parts):
                parent = '.'.join([action, *parts[:index + 1]])
                original = menu.get(parent, {})
                result[parent] = {k: v for k, v in original.items() if k in ('label', 'icon', 'iconFont')}
                result[parent].setdefault('label', {'ai': 'AI', 'php': 'PHP', 'javascript': 'JavaScript', 'service': 'Services'}.get(part, part.title()))
            result[f'{category}.{app_id}'] = {
                'label': app['name'],
                'action': f'foot omadora-terminal-action omadora app {action} {app_id}',
                'when': f'{"! " if action == "install" else ""}omadora app installed {app_id}',
            }
            if action == 'install' and app.get('repeatable'):
                result[f'{category}.{app_id}'].pop('when')
            if action == 'remove' and app_id in ('copr-package', 'preinstalls'):
                del result[f'{category}.{app_id}']
    icons = {'package': '', 'tui': '', 'copr-package': '', 'windows': '',
             'preinstalls': '󰄬', 'webapp': '', 'style': '󰏘', 'theme': '󰏘',
             'background': '', 'gaming': '', 'ai': '󰧑', 'editor': '',
             'terminal': '', 'development': '', 'service': '', 'font': ''}
    brands = read_json(ROOT / 'assets/icons/brands.json')
    for key, entry in result.items():
        if key.startswith(('install.', 'remove.')):
            app_id = key.rsplit('.', 1)[-1]
            slug = brands['apps'].get(app_id)
            if slug:
                entry['icon'] = chr(brands['icons'][slug]['codepoint'])
                entry['iconFont'] = brands['family']
                continue
            # Remove entries need the same brand glyph as their Install entry.
            original = menu.get(key) or menu.get('install.' + key.split('.', 1)[1], {})
            if not entry.get('icon'):
                entry['icon'] = original.get('icon') or icons.get(key.rsplit('.', 1)[-1], '')
            if original.get('iconFont'):
                entry.setdefault('iconFont', original['iconFont'])
    if 'install.webapp' in result:
        result['install.webapp']['action'] = 'foot omadora-terminal-action omarchy-webapp-install'
    result['trigger.capture.screenrecord'] = {'label': 'Screen recording', 'icon': ''}
    for suffix, label, flags in (('region', 'Select region', ''), ('fullscreen', 'Full screen', '--fullscreen'),
                                 ('desktop-audio', 'Region with desktop audio', '--with-desktop-audio'),
                                 ('microphone', 'Region with microphone', '--with-microphone-audio')):
        result['trigger.capture.screenrecord.' + suffix] = {'label': label, 'icon': '',
            'action': ('omarchy-capture-screenrecording ' + flags).strip(),
            'when': '! omarchy-capture-screenrecording --status'}
    result['trigger.capture.screenrecord.stop'] = {'label': 'Stop recording', 'icon': '',
        'action': 'omarchy-capture-screenrecording --stop-recording', 'when': 'omarchy-capture-screenrecording --status'}
    result['update'] = {'label': 'Update', 'icon': ''}
    result['update.fedora'] = {'label': 'Fedora packages', 'action': 'foot omadora-terminal-action omarchy-update'}
    result['update.flatpak'] = {'label': 'Flatpak apps', 'action': 'foot --hold flatpak update --user'}
    # Remove empty parent menus after pruning unsupported actions.
    for key in sorted(list(result), key=lambda s: s.count('.'), reverse=True):
        item = result[key]
        if not any(k in item for k in ('action', 'provider', 'target')) and not any(
                child.startswith(key + '.') for child in result):
            del result[key]
    return result


def package_commands(action, names):
    if action not in ('install', 'remove') or not names or any(
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', name) for name in names):
        raise ValueError('Enter package names separated by spaces, without options or URLs')
    return ['sudo', 'dnf', action, *names]


def choose_packages(action):
    print('Loading available packages from enabled repositories...' if action == 'install' else 'Loading installed packages...', flush=True)
    command = ('dnf', '-q', 'repoquery', '--available', '--queryformat', '%{name}\n') if action == 'install' else ('rpm', '-qa', '--queryformat', '%{NAME}\n')
    raw = run(*command, capture=True).stdout
    names = sorted({line.strip() for line in raw.splitlines()
                    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', line.strip())})
    if not names:
        print('No packages found.')
        return []
    env = {k: v for k, v in os.environ.items() if not k.startswith('FZF_DEFAULT_')}
    picked = subprocess.run(['fzf', '--multi', '--layout=reverse', '--border', '--bind', 'result:first',
                             '--prompt', action.title() + ' package > ',
                             '--header', 'Type to filter | Tab: select multiple | Enter: review DNF transaction | Esc: cancel'],
                            input='\n'.join(names), text=True, stdout=subprocess.PIPE, env=env)
    if picked.returncode in (1, 130):
        return []
    picked.check_returncode()
    selected = list(dict.fromkeys(picked.stdout.splitlines()))
    if not set(selected) <= set(names):
        raise ValueError('Package picker returned an unknown package')
    return selected


def assemble(source, output):
    """Construct a reviewable install tree. Never run upstream install/migrations."""
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('Build output must not already exist')
    output.mkdir(parents=True)
    tree = output / 'upstream'
    for name in ('bin', 'config', 'default', 'themes', 'shell'):
        shutil.copytree(source / name, tree / name)
    for name in ('LICENSE', 'version'):
        shutil.copy2(source / name, tree / name)
    for name in ('omadora.py', 'omadora_deploy.py', 'omadora_lifecycle.py', 'omadora_optional.py',
                 'omadora_workflows.py', 'apps.json', 'optional.json', 'upstream.lock.json'):
        shutil.copy2(ROOT / name, output / name)
    write(output / 'release.json', json.dumps({'version': VERSION, 'revision': lifecycle().revision(ROOT)}))
    shutil.copytree(ROOT / 'packages', output / 'packages')
    shutil.copytree(ROOT / 'assets', output / 'assets')
    # Load from the versioned runtime so upgrades/rollbacks do not depend on
    # refreshing an old per-user copy of the font or changing the user's theme.
    menu_qml = tree / 'shell/plugins/menu/Menu.qml'
    write(menu_qml, menu_qml.read_text(encoding='utf-8').replace('  id: root\n',
        '  id: root\n\n  FontLoader { source: "../../../../assets/fonts/OmadoraAppIcons.ttf" }\n', 1))

    # Keep upstream identifiers for compatibility. Only the product entrypoints
    # and menu branding are Omadora; wholesale textual renaming breaks IPC.
    env = ('export OMARCHY_PATH=/usr/local/share/omadora/upstream\n'
           'export PATH="/usr/local/share/omadora/bin:$OMARCHY_PATH/bin:$HOME/.local/bin:$PATH"\n'
           'export XDG_DATA_DIRS="/usr/local/share/omadora/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"\n'
           'export TERMINAL=foot\nexport EDITOR=nvim\n'
           # Set before UWSM activates portal/toolkit services, not only in
           # compositor child processes after asynchronous environment import.
           'export GDK_BACKEND="wayland,x11,*"\n'
           'export QT_QPA_PLATFORM="wayland;xcb"\n'
           'export QT_QPA_PLATFORMTHEME=gtk3\n'
           'export MOZ_ENABLE_WAYLAND=1\n'
           'export ELECTRON_OZONE_PLATFORM_HINT=wayland\n'
           'export OZONE_PLATFORM=wayland\n')
    write(tree / 'default/bash/env-bootstrap', env)
    write(output / 'bin/omadora', '#!/bin/sh\nexec python3 /usr/local/share/omadora/omadora.py "$@"\n', 0o755)
    write(output / 'bin/uwsm-app', '#!/bin/sh\nexec uwsm app "$@"\n', 0o755)
    write(output / 'bin/powerprofilesctl', '#!/bin/sh\nexec python3 /usr/local/share/omadora/omadora.py powerprofile "$@"\n', 0o755)
    # Match Hyprland's packaged UWSM session: the desktop entry invokes its
    # supported start-hyprland watchdog and carries the desktop environment ID.
    session_activation = '''# GDM can leave its greeter on the active VT during a slow login.
# Activate only the authenticated local session supplied by the display manager.
if [[ -n ${XDG_SESSION_ID:-} && -n ${XDG_SEAT:-} ]]; then
  timeout 10 loginctl activate "$XDG_SESSION_ID" || exit 1
  for ((attempt=0; attempt<50; attempt++)); do
    [[ $(loginctl show-session "$XDG_SESSION_ID" -p Active --value) == yes ]] && break
    sleep 0.1
  done
  if [[ $(loginctl show-session "$XDG_SESSION_ID" -p Active --value) != yes ]]; then
    echo 'Omadora: the login session did not become active.' >&2
    exit 1
  fi
fi
'''
    write(output / 'bin/omadora-session', '#!/bin/bash\n' + env + session_activation + 'exec uwsm start -e -D Hyprland -- /usr/share/wayland-sessions/hyprland.desktop\n', 0o755)

    overrides = {
        # The pinned helper is portable; an Arch-only comment previously caused
        # the conservative command scanner to block it.
        'omarchy-theme-set-gnome': '\n'.join(line for line in
            (source / 'bin/omarchy-theme-set-gnome').read_text().splitlines()
            if not line.lstrip().startswith('#')),
        'omarchy-launch-terminal': 'exec setsid uwsm-app -- foot "$@"',
        'omarchy-launch-browser': 'args=("$@"); for i in "${!args[@]}"; do [[ ${args[$i]} == --private ]] && args[$i]=--private-window; done; exec uwsm-app -- firefox "${args[@]}"',
        'omarchy-launch-webapp': 'exec uwsm-app -- firefox "$@"',
        'omarchy-voxtype-config': 'if ! command -v voxtype >/dev/null; then exec foot omadora-terminal-action omadora app install dictation; fi\nomarchy-launch-floating-terminal-with-presentation "voxtype configure"',
        'omarchy-launch-about': 'exec foot --hold omadora about',
        'omarchy-update': 'exec omadora update',
        'omarchy-update-available': 'exec omadora updates-available',
        'omarchy-update-status': 'exec omarchy-shell -q omarchy.system-update refresh',
        'omarchy-pkg-present': 'exec omadora pkg-present "$@"',
        'omarchy-pkg-missing': 'omadora pkg-present "$@" && exit 1; exit 0',
        'omarchy-provision-first-run': ': # Omadora seeds only minimal desktop configuration.',
    }
    blocked = []
    for path in (tree / 'bin').iterdir():
        if not path.is_file():
            continue
        content = path.read_text(encoding='utf-8')
        if path.name in overrides:
            write(path, '#!/bin/bash\n' + overrides[path.name] + '\n', 0o755)
        elif path.name.startswith(UNPORTED) or DISALLOWED.search(content):
            blocked.append(path.name)
            write(path, '#!/bin/bash\necho "This system operation is not ported to Omadora. Use the Fedora Install/Update menu." >&2\nexit 1\n', 0o755)
        else:
            path.chmod(0o755)
    # Auth stack delegates to Fedora's authselect-managed system-auth.
    write(output / 'system/omarchy-lock-password', '#%PAM-1.0\nauth include system-auth\naccount include system-auth\n')
    write(output / 'system/omadora.desktop', '[Desktop Entry]\nName=Omadora\nComment=Minimal Omarchy 4 desktop for Fedora\nExec=/usr/local/bin/omadora-session\nType=Application\nDesktopNames=Hyprland;\n')
    write(output / 'system/omadora-env', env)
    # gnome-themes-extra supplies this name upstream. Use GTK's own bundled
    # dark stylesheet without pulling obsolete GTK2 theme dependencies.
    write(output / 'share/themes/Adwaita-dark/gtk-3.0/gtk.css',
          '@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css");\n')
    autostart = tree / 'default/hypr/autostart.lua'
    write(autostart, autostart.read_text().replace(
        'hl.exec_cmd("omarchy-launch-shell")',
        'hl.exec_cmd("omarchy-theme-set-gnome")\n  hl.exec_cmd("omarchy-launch-shell")'))
    hypr = tree / 'config/hypr/hyprland.lua'
    write(hypr, 'omarchy_preinstalled_bindings = false\n' + hypr.read_text(encoding='utf-8'))
    menu = menu_for_fedora(load_menu(tree / 'default/omarchy/omarchy-menu.jsonc'), read_json(ROOT / 'apps.json'), blocked)
    write(tree / 'default/omarchy/omarchy-menu.jsonc', json.dumps(menu, indent=2, ensure_ascii=False))
    shell_config = read_json(tree / 'config/omarchy/shell.json')
    for position, widgets in shell_config['bar']['layout'].items():
        shell_config['bar']['layout'][position] = [w for w in widgets if w['id'] != 'omarchy.agents']
    write(tree / 'config/omarchy/shell.json', json.dumps(shell_config, indent=2))
    foot = tree / 'config/foot/foot.ini'
    write(foot, foot.read_text().replace('JetBrainsMono Nerd Font', 'JetBrainsMonoNL Nerd Font'))
    # Keep absent optional programs out of the advertised keybindings.
    utilities = tree / 'default/hypr/bindings/utilities.lua'
    optional = ('omacalc', 'tmux-keybindings', 'herdr-keybindings', 'screenrecord',
                'webcam-resize', 'capture-text', 'omarchy-agent', 'omarchy-transcode',
                'omarchy-reminder', 'toggle reminder-set', 'toggle share')
    write(utilities, '\n'.join(line for line in utilities.read_text().splitlines()
                              if not any(token in line for token in optional)).replace('tui = "btop"', 'tui = "top"') + '\n')
    # The stock browser extensions are not installed in the minimal profile.
    keybindings = tree / 'bin/omarchy-menu-keybindings'
    text = keybindings.read_text(encoding='utf-8')
    text, count = re.subn(r'static_bindings\(\) \{\n.*?\n\}',
                         'static_bindings() {\n  :\n}', text, flags=re.S)
    if count != 1:
        raise ValueError('Upstream keybinding help changed; review the adapter')
    write(keybindings, text, 0o755)
    # Menu guards otherwise shadow our RPM helpers with an embedded Arch cache.
    model = tree / 'shell/plugins/menu/MenuModel.js'
    text = model.read_text(encoding='utf-8')
    text, count = re.subn(r'function guardHelpers\(\) \{\n.*?\n\}',
                         'function guardHelpers() {\n  // Use the installed Fedora helper commands.\n  return ""\n}',
                         text, flags=re.S)
    if count != 1:
        raise ValueError('Upstream menu guards changed; review the adapter')
    write(model, text)
    # Apple's HID brightness utility is not part of the Fedora profile. Try
    # ordinary DDC/CI instead of invoking a missing privileged vendor helper.
    brightness = tree / 'bin/omarchy-brightness-display'
    write(brightness, brightness.read_text().replace(
        '  omarchy-hyprland-monitor-focused-apple "$monitor"',
        '  command -v asdcontrol >/dev/null && omarchy-hyprland-monitor-focused-apple "$monitor"'), 0o755)
    # Browser policy tinting depends on upstream install helpers and a
    # privileged /usr/bin entrypoint. Fedora browsers retain their own policies.
    theme_set = tree / 'bin/omarchy-theme-set'
    write(theme_set, theme_set.read_text().replace('  omarchy-theme-set-browser\n', ''), 0o755)
    for name in ('omarchy-launch-tui', 'omarchy-launch-floating-terminal-with-presentation'):
        path = tree / 'bin' / name
        write(path, path.read_text().replace('xdg-terminal-exec', 'foot'), 0o755)
    # Font changes belong to the managed file covered by backup/restore, not
    # the user's general Fontconfig preferences, which may contain other rules.
    font_set = tree / 'bin/omarchy-font-set'
    write(font_set, font_set.read_text(encoding='utf-8').replace(
        '$HOME/.config/fontconfig/fonts.conf', '$HOME/' + FONT_CONFIG), 0o755)
    # A plain screenshot remains useful without preinstalling the annotation app.
    screenshot = tree / 'bin/omarchy-capture-screenshot'
    write(screenshot, (ROOT / 'assets/scripts/capture-screenshot').read_text(), 0o755)
    write(output / 'bin/omadora-terminal-action', (ROOT / 'assets/scripts/terminal-action').read_text(), 0o755)
    write(tree / 'bin/omarchy-capture-screenrecording', (ROOT / 'assets/scripts/screenrecord').read_text(), 0o755)
    recording = tree / 'shell/plugins/bar/indicators/ScreenRecording.qml'
    write(recording, recording.read_text().replace('["pgrep", "--quiet", "-f", "^gpu-screen-recorder"]',
                                                   '["omarchy-capture-screenrecording", "--status"]'))
    updates = tree / 'shell/plugins/bar/widgets/SystemUpdate.qml'
    write(updates, updates.read_text().replace('omarchy-launch-floating-terminal-with-presentation omarchy-update',
                                              'foot omadora-terminal-action omarchy-update').replace(
        'root.updateAvailable = exitCode === 0',
        'if (exitCode === 0 || exitCode === 1) root.updateAvailable = exitCode === 0'))
    # Explicit monospace fallback supplies Nerd glyphs to the unchanged shell.
    write(output / 'system/99-omadora-fonts.conf', '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n<fontconfig><alias><family>monospace</family><prefer><family>JetBrainsMonoNL Nerd Font</family></prefer></alias></fontconfig>\n')
    apply_branding(tree)
    write(output / 'portability-report.json', json.dumps({'blocked_commands': sorted(blocked),
          'upstream': read_json(ROOT / 'upstream.lock.json'), 'status': 'experimental; Fedora VM validation required'}, indent=2))
    return output


def apply_branding(tree):
    """Replace visible product words, retaining paths, IPC names and credits."""
    for path in tree.rglob('*'):
        if not path.is_file() or path.name in ('LICENSE', 'OFL.txt') or path.suffix in ('.md', '.ttf', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'):
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        lines = []
        for line in content.splitlines(keepends=True):
            if not re.search(r'copyright|"author"|"license"', line, re.IGNORECASE):
                line = re.sub(r'\bOmarchy\b', 'Omadora', line)
                line = line.replace('"OMARCHY"', '"OMADORA"').replace("'OMARCHY'", "'OMADORA'")
            lines.append(line)
        write(path, ''.join(lines))
    letters = {
        'O': [' ███ ', '█   █', '█   █', '█   █', ' ███ '],
        'M': ['█   █', '██ ██', '█ █ █', '█   █', '█   █'],
        'A': [' ███ ', '█   █', '█████', '█   █', '█   █'],
        'D': ['████ ', '█   █', '█   █', '█   █', '████ '],
        'R': ['████ ', '█   █', '████ ', '█  █ ', '█   █'],
    }
    logo = '\n'.join('  '.join(letters[letter][row] for letter in 'OMADORA') for row in range(5)) + '\n'
    write(tree / 'logo.txt', logo)
    write(tree / 'icon.txt', 'O\n')
    write(tree / 'config/omarchy/branding/screensaver.txt', logo)
    # The minimal profile uses Foot. Do not depend on GNOME's terminal default.
    launch = tree / 'bin/omarchy-launch-screensaver'
    write(launch, launch.read_text().replace('terminal=$(xdg-terminal-exec --print-id)', 'terminal=foot'), 0o755)
    foot = tree / 'default/foot/screensaver.ini'
    write(foot, foot.read_text().replace('JetBrainsMono Nerd Font', 'JetBrainsMonoNL Nerd Font'))


def backup_user(home, backup):
    """Copy exact config trees including symlinks; record absence for restore."""
    paths = [f'.config/{name}' for name in CONFIGS] + ['.config/uwsm/env-hyprland', '.local/state/omarchy', FONT_CONFIG, '.local/share/fonts/omadora']
    manifest = []
    for relative in paths:
        source = home / relative
        exists = source.exists() or source.is_symlink()
        manifest.append({'path': relative, 'existed': exists})
        if exists:
            dest = backup / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                dest.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
            elif source.is_dir():
                shutil.copytree(source, dest, symlinks=True)
            else:
                shutil.copy2(source, dest)
    write(backup / 'manifest.json', json.dumps(manifest, indent=2))


def restore_user(home, backup):
    allowed = {f'.config/{name}' for name in CONFIGS} | {'.config/uwsm/env-hyprland', '.local/state/omarchy'}
    manifest = read_json(backup / 'manifest.json')
    paths = {entry['path'] for entry in manifest}
    # Backups made before the font integration fix remain restorable.
    if paths not in (allowed, allowed | {FONT_CONFIG}, allowed | {FONT_CONFIG, '.local/share/fonts/omadora'}) or len(manifest) != len(paths):
        raise ValueError('Invalid backup manifest')
    # A parent may have been replaced with a symlink since installation.
    # Never follow it while removing managed paths or writing the rescue copy.
    for relative in paths | {'.local/state/omadora/backups/rescue'}:
        for parent in Path(relative).parents:
            if (home / parent).is_symlink():
                raise ValueError(f'Restore target parent must not be a symlink: ~/{parent}')
    for entry in manifest:
        saved = backup / entry['path']
        if entry['existed'] and not (saved.exists() or saved.is_symlink()):
            raise ValueError(f'Backup is incomplete: {saved}')
    # Preserve edits made since installation before restoring old configuration.
    rescue = home / '.local/state/omadora/backups' / ('before-restore-' + timestamp())
    backup_user(home, rescue)
    for entry in manifest:
        dest, saved = home / entry['path'], backup / entry['path']
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)
        if entry['existed']:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if saved.is_symlink():
                dest.symlink_to(os.readlink(saved), target_is_directory=saved.is_dir())
            elif saved.is_dir():
                shutil.copytree(saved, dest, symlinks=True)
            else:
                shutil.copy2(saved, dest)
    return rescue


def desktop_settings(action, backup):
    """Save/restore only the three interface keys modified by theme switching."""
    path = backup / 'desktop-settings.json'
    env = os.environ.copy()
    bus = Path('/run/user') / str(os.getuid()) / 'bus' if hasattr(os, 'getuid') else None
    if not env.get('DBUS_SESSION_BUS_ADDRESS') and bus and bus.is_socket():
        env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=' + str(bus)
    if action == 'save':
        values = {key: run('gsettings', 'get', 'org.gnome.desktop.interface', key,
                           capture=True, env=env).stdout.strip() for key in DESKTOP_KEYS}
        write(path, json.dumps(values, indent=2))
    elif path.exists():
        values = read_json(path)
        if set(values) != set(DESKTOP_KEYS) or not all(isinstance(v, str) for v in values.values()):
            raise ValueError('Invalid desktop settings backup')
        # A bare TTY/container can lack a user bus. gsettings otherwise prints
        # a dconf warning yet exits zero without saving anything.
        prefix = [] if env.get('DBUS_SESSION_BUS_ADDRESS') else ['dbus-run-session', '--']
        for key, value in values.items():
            run(*prefix, 'gsettings', 'set', 'org.gnome.desktop.interface', key, value, env=env)
            actual = run('gsettings', 'get', 'org.gnome.desktop.interface', key, capture=True, env=env).stdout.strip()
            if actual != value:
                raise ValueError('Desktop preference was not restored: ' + key)


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def steam_certificates(bundle=Path('/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem'),
                       alias=Path('/etc/pki/tls/cert.pem')):
    """Steam's native updater still reads Fedora's former certificate path."""
    if os.path.lexists(alias):
        if not alias.is_file():
            raise ValueError(f'Existing certificate path is not a readable file: {alias}')
        return  # Never replace an administrator's trust configuration.
    if not bundle.is_file():
        raise ValueError(f'Fedora certificate bundle is missing: {bundle}')
    # A live link follows ca-certificates updates; no copied or alternate roots,
    # no deprecated update-ca-trust flag, and no disabled TLS verification.
    run('sudo', 'ln', '-s', bundle, alias)
    print(f'Steam compatibility: {alias} now points to Fedora’s maintained CA bundle.')


def fetch_upstream(destination):
    lock = read_json(ROOT / 'upstream.lock.json')
    run('git', 'init', destination)
    run('git', '-C', destination, 'remote', 'add', 'origin', lock['repository'])
    run('git', '-C', destination, 'fetch', '--depth', '1', 'origin', lock['tag'])
    actual = run('git', '-C', destination, 'rev-parse', 'FETCH_HEAD^{commit}', capture=True).stdout.strip()
    if actual != lock['commit']:
        raise ValueError('Upstream tag no longer matches the pinned commit')
    run('git', '-C', destination, 'checkout', '--detach', actual)


def lifecycle():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import omadora_lifecycle
    return omadora_lifecycle


def install(dry_run=False):
    if dry_run:
        print(json.dumps({'target': 'Fedora Workstation 44 x86_64', 'upstream': read_json(ROOT / 'upstream.lock.json'),
                          'coprs': [COPR, SCREENSAVER_COPR], 'packages': packages(), 'prefix': str(PREFIX),
                          'optional_apps_preinstalled': [], 'gnome_removed': False}, indent=2))
        return
    return lifecycle().perform(sys.modules[__name__], 'install')


def prepare_runtime(temp):
    run('sudo', 'dnf', 'install', '-y', 'dnf5-plugins')
    run('sudo', 'dnf', 'copr', 'enable', '-y', COPR)
    run('sudo', 'dnf', 'copr', 'enable', '-y', SCREENSAVER_COPR)
    # DNF's complete transaction must resolve. Never skip broken packages.
    run('sudo', 'dnf', 'install', '-y', *packages())
    # Hyprland initializes its logger before processing --version and needs
    # XDG_RUNTIME_DIR even for this non-graphical probe (e.g. over SSH).
    probe_env = os.environ.copy()
    if not probe_env.get('XDG_RUNTIME_DIR'):
        runtime = temp / 'runtime'
        runtime.mkdir(mode=0o700)
        probe_env['XDG_RUNTIME_DIR'] = str(runtime)
    version = run('Hyprland', '--version', capture=True, env=probe_env).stdout
    match = re.search(r'\b(\d+)\.(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (0, 55, 0):
        raise ValueError('Omarchy 4 Lua configuration requires Hyprland >= 0.55. Desktop files were not installed.')
    for command in ('quickshell', 'uwsm', 'foot', 'gum', 'jq', 'nvim'):
        if not shutil.which(command):
            raise ValueError(f'Missing required executable: {command}')
    return probe_env


def _install():
    preflight()
    for relative in ('.config', '.config/uwsm', '.local', '.local/state', '.local/state/omarchy',
                     '.local/share', '.local/share/fonts', '.local/share/fonts/omadora',
                     '.config/fontconfig', '.config/fontconfig/conf.d'):
        if (Path.home() / relative).is_symlink():
            raise ValueError(f'Fresh-install target must not be a symlink: ~/{relative}')
    if os.path.lexists(PREFIX):
        raise ValueError('Omadora is already installed. Use omadora upgrade from GNOME or a TTY.')
    for path in ('/usr/local/bin/omadora', '/usr/local/bin/omadora-session',
                 '/usr/share/wayland-sessions/omadora.desktop', '/etc/pam.d/omarchy-lock-password'):
        if os.path.lexists(path):
            raise ValueError(f'Refusing to replace an existing system file: {path}')
    print('Omadora development build: adds nett00n/hyprland and whelanh/omarchy COPRs (ttfx screensaver), plus a GDM session. See docs/VALIDATION.md for test coverage and remaining limitations.', flush=True)
    with tempfile.TemporaryDirectory(prefix='omadora-') as temporary:
        temp = Path(temporary)
        fetch_upstream(temp / 'source')
        stage = assemble(temp / 'source', temp / 'stage')
        probe_env = prepare_runtime(temp)
        home = Path.home()
        transaction = lifecycle().prepare(sys.modules[__name__], 'install')
        lifecycle().root(sys.modules[__name__], 'deploy', transaction['id'], stage)
        # Config directories were backed up. Unlink whole destinations to avoid
        # copying through user symlinks into unrelated locations.
        for name in CONFIGS:
            dest = home / '.config' / name
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            elif dest.is_dir():
                shutil.rmtree(dest)
            shutil.copytree(PREFIX / 'upstream/config' / name, dest)
        uwsm_env = home / '.config/uwsm/env-hyprland'
        if uwsm_env.is_symlink():
            uwsm_env.unlink()
        write(uwsm_env, (PREFIX / 'system/omadora-env').read_text())
        fonts = home / '.local/share/fonts/omadora'
        fonts.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PREFIX / 'upstream/default/fonts/omarchy/omarchy.ttf', fonts / 'omarchy.ttf')
        for font in (PREFIX / 'assets/fonts').glob('*.ttf'):
            shutil.copy2(font, fonts / font.name)
        # Use standard user font configuration. A session-wide FONTCONFIG_FILE
        # leaks an inaccessible host path into Flatpak sandboxes.
        font_config = home / FONT_CONFIG
        if font_config.is_symlink():
            font_config.unlink()
        write(font_config, (PREFIX / 'system/99-omadora-fonts.conf').read_text())
        run('fc-cache', '-f', fonts)
        env = dict(os.environ, OMARCHY_PATH=str(PREFIX / 'upstream'), OMARCHY_THEME_HEADLESS='1',
                   XDG_RUNTIME_DIR=probe_env['XDG_RUNTIME_DIR'],
                   PATH=f'{PREFIX}/bin:{PREFIX}/upstream/bin:' + os.environ['PATH'])
        run(PREFIX / 'upstream/bin/omarchy-theme-set', 'tokyo-night', env=env)
        run('Hyprland', '--verify-config', '--config', home / '.config/hypr/hyprland.lua', env=env)
        # Publish the login session last, after successful config/theme setup.
        lifecycle().root(sys.modules[__name__], 'activate', transaction['id'])
        run('sudo', 'restorecon', '-RF', PREFIX, '/etc/pam.d/omarchy-lock-password', '/usr/share/wayland-sessions/omadora.desktop')
        lifecycle().commit(sys.modules[__name__], transaction)
    print('Installed. Log out and select Omadora at the GDM gear menu. GNOME remains available.')


def installed(app):
    if app['source'] == 'optional':
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        import omadora_optional
        return omadora_optional.installed(app['recipe'])
    if app['source'] == 'flatpak':
        if not shutil.which('flatpak'):
            return False
        return run('flatpak', 'info', '--user', app['id'], capture=True, check=False).returncode == 0
    if not shutil.which('rpm'):
        return False
    return run('rpm', '-q', *app['packages'], capture=True, check=False).returncode == 0


def powerprofile(action, profile=None):
    # Fedora's TuneD implements the standard PPD D-Bus API but does not ship
    # powerprofilesctl. Supply only the get/list/set operations upstream uses.
    import dbus
    interface = 'net.hadess.PowerProfiles'
    obj = dbus.SystemBus().get_object(interface, '/net/hadess/PowerProfiles')
    properties = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    profiles = [str(item['Profile']) for item in properties.Get(interface, 'Profiles')]
    if action == 'set':
        if profile not in profiles:
            raise ValueError('Power profile is not available: ' + str(profile))
        properties.Set(interface, 'ActiveProfile', dbus.String(profile, variant_level=1))
    elif action == 'get':
        print(properties.Get(interface, 'ActiveProfile'))
    else:
        active = str(properties.Get(interface, 'ActiveProfile'))
        for name in profiles:
            print(('* ' if name == active else '  ') + name + ':')


def main():
    parser = argparse.ArgumentParser(description='Omadora: minimal Omarchy 4 for Fedora')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('install'); p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('upgrade'); p.add_argument('--local', action='store_true', help='Use this source checkout'); p.add_argument('--ref', default=RELEASE_REF)
    sub.add_parser('recover'); sub.add_parser('rollback')
    p = sub.add_parser('build'); p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('app'); p.add_argument('action', choices=('list', 'install', 'remove', 'installed')); p.add_argument('id', nargs='?'); p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('package'); p.add_argument('action', choices=('install', 'remove')); p.add_argument('names', nargs='*'); p.add_argument('--dry-run', action='store_true')
    sub.add_parser('about'); sub.add_parser('update'); sub.add_parser('updates-available'); sub.add_parser('doctor')
    p = sub.add_parser('pkg-present'); p.add_argument('packages', nargs='+')
    p = sub.add_parser('powerprofile'); p.add_argument('action', choices=('get', 'list', 'set')); p.add_argument('profile', nargs='?')
    p = sub.add_parser('restore-config'); p.add_argument('backup', type=Path)
    args = parser.parse_args()
    if args.command == 'install':
        install(args.dry_run)
    elif args.command == 'upgrade':
        lifecycle().upgrade(sys.modules[__name__], args.local, args.ref)
    elif args.command in ('recover', 'rollback'):
        lifecycle().perform(sys.modules[__name__], args.command)
    elif args.command == 'build':
        print(assemble(args.source, args.output))
    elif args.command == 'package':
        names = args.names or choose_packages(args.action)
        if not names:
            return 0
        command = package_commands(args.action, names)
        if args.dry_run:
            print(shlex.join(command))
        else:
            run(*command)
    elif args.command == 'about':
        print(f'Omadora {VERSION} | Omarchy 4.0.4 | Fedora Workstation 44\nIndependent minimal Fedora port. Experimental; see docs/VALIDATION.md for tested behavior and known failures.\nhttps://github.com/DanielCoffey1/omadora')
    elif args.command == 'app':
        apps = read_json(ROOT / 'apps.json')
        if args.action == 'list':
            for app_id, app in apps.items():
                print(f'{app_id:14} {app["category"]:15} {app["source"]:10} {app["name"]}')
        else:
            if args.id not in apps:
                raise ValueError('Unknown app. Run: omadora app list')
            app = apps[args.id]
            if args.action == 'installed':
                return 0 if installed(app) else 1
            commands = app_commands(app, args.action)
            if args.dry_run:
                print('\n'.join(shlex.join(c) for c in commands))
                if args.id == 'steam' and args.action == 'install':
                    print('If absent, add /etc/pki/tls/cert.pem link to Fedora’s maintained CA bundle for Steam.')
            else:
                preflight()
                for command in commands:
                    run(*command)
                if args.action == 'install' and app.get('unit'):
                    run('sudo', 'systemctl', 'enable', '--now', app['unit'])
                    if app.get('group'):
                        import getpass
                        run('sudo', 'usermod', '-aG', app['group'], getpass.getuser())
                        print('Sign out and back in to apply service group access.')
                    print('Service installed. Run the vendor login command to connect your account.')
                if args.id == 'steam' and args.action == 'install':
                    steam_certificates()
    elif args.command == 'pkg-present':
        aliases = {'nvim': 'neovim', 'fd': 'fd-find', 'networkmanager': 'NetworkManager', 'imagemagick': 'ImageMagick'}
        names = [aliases.get(p, p) for p in args.packages]
        if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9+_.-]*', p) for p in names):
            return 1
        return run('rpm', '-q', *names, capture=True, check=False).returncode
    elif args.command == 'powerprofile':
        powerprofile(args.action, args.profile)
    elif args.command == 'update':
        preflight()
        try:
            run('sudo', 'dnf', 'upgrade', '--refresh')
        finally:
            # Recheck even after a cancelled/partial transaction. Never clear an
            # outstanding update merely because the updater window was closed.
            if shutil.which('omarchy-shell'):
                try:
                    run('omarchy-shell', '-q', 'omarchy.system-update', 'refresh', check=False, capture=True)
                except OSError:
                    pass  # A missing/stopped desktop must not mask DNF's result.
        print('Fedora packages updated. Omadora desktop stays at its pinned release.')
    elif args.command == 'updates-available':
        result = run('dnf', '--cacheonly', 'check-upgrade', capture=True, check=False)
        if result.returncode == 100:
            print('Fedora updates available')
            return 0
        return 1 if result.returncode == 0 else 2
    elif args.command == 'restore-config':
        preflight()
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            raise ValueError('Log out of Hyprland and restore from GNOME or a TTY.')
        backup = args.backup.resolve()
        base = Path.home() / '.local/state/omadora/backups'
        if not backup.is_relative_to(base.resolve()):
            raise ValueError('Backup must be inside ~/.local/state/omadora/backups')
        rescue = restore_user(Path.home(), backup)
        desktop_settings('save', rescue)
        desktop_settings('restore', backup)
        print('Restored; current edits saved at', rescue)
    elif args.command == 'doctor':
        failed = False
        for executable in ('Hyprland', 'quickshell', 'uwsm', 'foot', 'nvim', 'gum', 'jq', 'grim', 'slurp'):
            found = shutil.which(executable)
            print(f'{executable}: {found or "MISSING"}')
            failed |= not bool(found)
        print('Upstream:', read_json(ROOT / 'upstream.lock.json')['commit'])
        print('Graphical login, PAM unlock, suspend and portals require a Fedora VM/hardware test.')
        return int(failed)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Omadora: {error}', file=sys.stderr)
        sys.exit(1)
