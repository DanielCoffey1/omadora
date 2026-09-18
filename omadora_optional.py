#!/usr/bin/python3
"""Optional application lifecycle. Downloads are pinned; user data is retained."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent


def run(*args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def recipes():
    return json.loads((ROOT / 'optional.json').read_text())


def location(key):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', key):
        raise ValueError('Invalid optional application identifier')
    path = Path.home() / '.local/share/omadora/optional' / key
    # Refuse redirected storage before any download, replacement or deletion.
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Optional application storage must not use symlinks: ' + str(parent))
    return path


def installed(key):
    recipe = recipes()[key]
    if recipe['kind'] == 'rpm':
        return shutil.which('rpm') and subprocess.run(['rpm', '-q', recipe['package']],
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    path = location(key)
    return (path / 'installed.json').is_file()


def download(spec, target):
    url = spec['url']
    algorithm = 'sha256' if spec.get('sha256') else 'sha512'
    digest = spec.get(algorithm, '')
    if not url.startswith('https://') or not re.fullmatch('[0-9a-f]{' + str(64 if algorithm == 'sha256' else 128) + '}', digest):
        raise ValueError('Download needs an HTTPS URL and a pinned checksum')
    hasher = hashlib.new(algorithm)
    request = urllib.request.Request(url, headers={'User-Agent': 'Omadora/0.1'})
    with urllib.request.urlopen(request, timeout=90) as response, target.open('wb') as out:
        if not response.url.startswith('https://'):
            raise ValueError('Refusing an insecure download redirect')
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
            hasher.update(chunk)
    if hasher.hexdigest() != digest:
        target.unlink()
        raise ValueError('Download checksum mismatch: ' + url)


def extract_tar(archive, destination):
    # tarfile's data filter rejects devices, escaping links and traversal.
    # Absolute package symlinks are made relative inside the relocated payload.
    with tarfile.open(archive) as source:
        for member in source:
            if member.issym() and member.linkname.startswith('/'):
                member.linkname = os.path.relpath(member.linkname.lstrip('/'),
                                                  str(PurePosixPath(member.name).parent))
            source.extract(member, destination, filter='data')


def unpack(archive, destination, kind):
    destination.mkdir(parents=True, exist_ok=True)
    if kind == 'zip':
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                name = PurePosixPath(member.filename)
                if name.is_absolute() or '..' in name.parts or '\\' in member.filename:
                    raise ValueError('Unsafe ZIP member')
            source.extractall(destination)
    elif kind == 'deb':
        # bsdtar reads ar; Debian maintainer scripts are never executed.
        entries = subprocess.check_output(['bsdtar', '-tf', str(archive)], text=True).splitlines()
        data = [x for x in entries if re.fullmatch(r'data\.tar\.(xz|gz|zst)', x)]
        if len(data) != 1:
            raise ValueError('Unexpected Debian archive layout')
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / data[0]
            with payload.open('wb') as out:
                run('bsdtar', '-xOf', archive, data[0], stdout=out)
            unpack(payload, destination, 'tar.zst' if data[0].endswith('zst') else 'tar')
    elif kind == 'tar.zst':
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / 'payload.tar'
            with payload.open('wb') as out:
                run('zstd', '-dc', archive, stdout=out)
            extract_tar(payload, destination)
    else:
        extract_tar(archive, destination)


def desktop_arg(value):
    if '\n' in value or '\r' in value:
        raise ValueError('Desktop arguments must fit one line')
    # Exec field quoting, followed by desktop-file string escaping.
    value = value.replace('%', '%%')
    value = ''.join('\\' + c if c in '\\"`$' else c for c in value)
    return ('"' + value + '"').replace('\\', '\\\\')


def launcher(key, name, command, terminal=False):
    if '\n' in name or '\r' in name:
        raise ValueError('Invalid launcher name')
    path = Path.home() / '.local/share/applications' / ('omadora-' + key + '.desktop')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and 'X-Omadora-Managed=true' not in path.read_text()):
        raise ValueError('Refusing to overwrite a foreign launcher: ' + str(path))
    if terminal:
        command = ['foot', *command]
    path.write_text('[Desktop Entry]\nType=Application\nName=' + name.replace('\\', '\\\\') +
                   '\nExec=' + ' '.join(desktop_arg(str(x)) for x in command) +
                   '\nIcon=application-x-executable\nTerminal=false\nX-Omadora-Managed=true\n')


def command_link(key, command, launch_args=()):
    """Expose a CLI without replacing an existing user's command."""
    path = Path.home() / '.local/bin' / command
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = '# Omadora optional: ' + key
    if path.is_symlink() or (path.exists() and marker not in path.read_text(errors='replace')):
        raise ValueError('An existing command is not owned by Omadora: ' + str(path))
    path.write_text('#!/bin/sh\n' + marker + '\nexec python3 ' + shlex.quote(str(ROOT / 'omadora_optional.py')) +
                    ' launch ' + shlex.join([key, *launch_args]) + ' "$@"\n')
    path.chmod(0o755)


@contextlib.contextmanager
def locked(key):
    import fcntl
    root = location(key).parent
    root.mkdir(parents=True, exist_ok=True)
    with (root / ('.' + key + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def asset_install(key, recipe):
    final = location(key)
    if final.exists():
        if not (final / 'installed.json').exists():
            pending = final / 'pending.json'
            if not pending.is_file() or json.loads(pending.read_text()).get('recipe') != recipe:
                raise ValueError('Unrecognized or different incomplete installation retained at ' + str(final))
            register_asset(key, recipe, final)
            return
        print('Already installed. Remove this app before installing another pinned version; application data is retained.')
        return
    dependencies = recipe.get('dependencies', [])
    if dependencies:
        run('sudo', 'dnf', 'install', *dependencies)
    with tempfile.TemporaryDirectory(prefix='.' + key + '-', dir=final.parent) as tmp:
        stage = Path(tmp)
        artifact = stage / 'download'
        download(recipe, artifact)
        payload = stage / 'payload'
        payload.mkdir()
        kind = recipe['kind']
        if kind == 'rpm':
            rpm = stage / 'download.rpm'
            artifact.rename(rpm)
            run('sudo', 'dnf', 'install', rpm)
            return
        if kind in ('binary', 'appimage'):
            binary = payload / recipe.get('executable', 'app')
            shutil.move(artifact, binary)
            binary.chmod(0o755)
        else:
            unpack(artifact, payload, recipe.get('archive', 'tar'))
        executable = recipe.get('executable')
        if executable and not (payload / executable).is_file():
            raise ValueError('Expected executable missing: ' + executable)
        if executable:
            (payload / executable).chmod((payload / executable).stat().st_mode | 0o755)
        # Stage first; no half-downloaded tree becomes an installed application.
        (payload / 'pending.json').write_text(json.dumps({'recipe': recipe}))
        payload.rename(final)
    register_asset(key, recipe, final)


def register_asset(key, recipe, final):
    if recipe['kind'] == 'font':
        fontdir = Path.home() / '.local/share/fonts' / ('omadora-' + key)
        if not (fontdir.is_symlink() and fontdir.resolve() == final):
            if fontdir.exists() or fontdir.is_symlink():
                raise ValueError('Font directory already exists: ' + str(fontdir))
            fontdir.parent.mkdir(parents=True, exist_ok=True)
            fontdir.symlink_to(final, target_is_directory=True)
        run('fc-cache', '-f')
    else:
        if recipe.get('command'):
            command_link(key, recipe['command'])
        launcher(key, recipe['name'], ['python3', str(ROOT / 'omadora_optional.py'), 'launch', key], recipe.get('terminal', False))
    (final / 'installed.json').write_text(json.dumps({'recipe': recipe, 'version': recipe.get('version')}))
    (final / 'pending.json').unlink(missing_ok=True)


def remove(key, recipe):
    if recipe['kind'] == 'rpm':
        run('sudo', 'dnf', 'remove', recipe['package'])
        return
    final = location(key)
    if not final.exists():
        return
    marker = final / 'installed.json'
    if not marker.is_file():
        marker = final / 'pending.json'
    if not marker.is_file() or 'recipe' not in json.loads(marker.read_text()):
        raise ValueError('Refusing to remove an unrecognized installation: ' + str(final))
    recipe = json.loads(marker.read_text())['recipe']
    if recipe['kind'] == 'workflow':
        import omadora_workflows
        omadora_workflows.remove(key, final)
    for command in recipe.get('commands', [recipe['command']] if recipe.get('command') else []):
        link = Path.home() / '.local/bin' / command
        if link.is_file() and not link.is_symlink() and '# Omadora optional: ' + key in link.read_text(errors='replace'):
            link.unlink()
    desktop = Path.home() / '.local/share/applications' / ('omadora-' + key + '.desktop')
    if desktop.is_file() and not desktop.is_symlink() and 'X-Omadora-Managed=true' in desktop.read_text():
        desktop.unlink()
    if recipe['kind'] == 'font':
        fontdir = Path.home() / '.local/share/fonts' / ('omadora-' + key)
        if fontdir.is_symlink() and fontdir.resolve() == final:
            fontdir.unlink()
    shutil.rmtree(final)
    if recipe['kind'] == 'font':
        run('fc-cache', '-f')
    print('Removed managed application files. Personal settings, models, games and database volumes are retained.')


def launch(key, recipe, args):
    if recipe['kind'] == 'workflow':
        import omadora_workflows
        return omadora_workflows.launch(key, location(key), args)
    executable = location(key) / recipe.get('executable', 'app')
    env = dict(os.environ)
    if recipe['kind'] == 'appimage':
        env['APPIMAGE_EXTRACT_AND_RUN'] = '1'
    os.execvpe(str(executable), [str(executable), *recipe.get('args', []), *args], env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['install', 'remove', 'launch', 'plan'])
    parser.add_argument('key', choices=recipes())
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    recipe = recipes()[args.key]
    if args.action == 'plan':
        print(json.dumps(recipe, indent=2)); return
    if args.action == 'launch':
        return launch(args.key, recipe, args.args)
    if os.geteuid() == 0:
        raise ValueError('Run as your desktop user; only package/system steps request sudo')
    with locked(args.key):
        if args.action == 'remove':
            remove(args.key, recipe)
        elif recipe['kind'] == 'workflow':
            import omadora_workflows
            final = location(args.key)
            if final.exists() and not any((final / marker).is_file() for marker in ('installed.json', 'pending.json')):
                raise ValueError('Unrecognized installation retained at ' + str(final))
            final.mkdir(exist_ok=True)
            (final / 'pending.json').write_text(json.dumps({'recipe': recipe}))
            omadora_workflows.install(args.key, final)
            (final / 'installed.json').write_text(json.dumps({'recipe': recipe}))
            (final / 'pending.json').unlink(missing_ok=True)
        else:
            asset_install(args.key, recipe)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, EOFError) as error:
        raise SystemExit('Omadora: ' + str(error))
