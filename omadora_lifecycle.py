"""Unprivileged lifecycle orchestration; privileged targets live in deploy helper."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

from omadora_deploy import atomic_json


def state_dir():
    return Path.home() / '.local/state/omadora'


def safe_home():
    for relative in ('.config', '.config/uwsm', '.local', '.local/state',
                     '.local/state/omadora', '.local/state/omadora/backups',
                     '.local/state/omarchy', '.local/share', '.local/share/fonts',
                     '.local/share/fonts/omadora', '.config/fontconfig', '.config/fontconfig/conf.d'):
        if (Path.home() / relative).is_symlink():
            raise ValueError('Lifecycle target must not be a symlink: ~/' + relative)


@contextlib.contextmanager
def locked():
    import fcntl
    safe_home()
    state_dir().mkdir(parents=True, exist_ok=True)
    path = state_dir() / 'lifecycle.lock'
    if path.is_symlink():
        raise ValueError('Lifecycle lock must not be a symlink.')
    with path.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another Omadora install, upgrade or recovery is running.')
        yield


def offline(a):
    if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') or a.run('pgrep', '-x', 'Hyprland', capture=True, check=False).returncode == 0:
        raise ValueError('Log out of every Hyprland session; use GNOME or a TTY for desktop maintenance.')


def root(a, action, token='status', stage=None):
    args = ['sudo', 'python3', getattr(a, '_deploy_helper', a.ROOT / 'omadora_deploy.py'), action, token]
    if stage is not None:
        args += ['--stage', stage]
    result = a.run(*args, capture=action in ('status', 'previous'))
    return json.loads(result.stdout) if action in ('status', 'previous') else None


def revision(source):
    import subprocess
    if (source / '.git').exists():
        return subprocess.check_output(['git', '-c', 'safe.directory=' + str(source), '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    metadata = source / 'release.json'
    return json.loads(metadata.read_text()).get('revision', 'local') if metadata.exists() else 'local'


def ensure_ready(a):
    if (state_dir() / 'transaction.json').exists() or root(a, 'status'):
        raise ValueError('An interrupted operation needs recovery. Run omadora recover first.')


def prepare(a, operation):
    ensure_ready(a)
    backup = state_dir() / 'backups' / (operation + '-' + a.timestamp())
    a.backup_user(Path.home(), backup)
    a.desktop_settings('save', backup)
    old = state_dir() / 'installation.json'
    transaction = {'id': uuid.uuid4().hex, 'operation': operation, 'phase': 'planned',
                   'backup': str(backup), 'previous': a.read_json(old) if old.exists() else None}
    atomic_json(state_dir() / 'transaction.json', transaction)
    root(a, 'begin', transaction['id'])
    transaction['phase'] = 'applying'
    atomic_json(state_dir() / 'transaction.json', transaction)
    print('Recovery snapshot:', backup, flush=True)
    return transaction


def commit(a, transaction, installed_revision=None):
    previous = transaction['previous'] or {}
    installation = dict(previous, backup=previous.get('backup', transaction['backup']),
                        upstream=a.read_json(a.PREFIX / 'upstream.lock.json'),
                        revision=installed_revision or revision(a.ROOT), status='installed')
    atomic_json(state_dir() / 'installation.json', installation)
    transaction['phase'] = 'committing'
    atomic_json(state_dir() / 'transaction.json', transaction)
    root(a, 'finish', transaction['id'])
    (state_dir() / 'transaction.json').unlink()


def recover(a):
    path = state_dir() / 'transaction.json'
    pending = root(a, 'status')
    if not path.exists():
        if pending:
            raise ValueError('System deployment is pending but this user has no matching journal. Use the user who started it.')
        print('No interrupted Omadora deployment found.')
        return
    transaction = a.read_json(path)
    if transaction.get('operation') not in ('install', 'upgrade', 'rollback') or transaction.get('phase') not in ('planned', 'applying', 'committing', 'restored'):
        raise ValueError('Invalid lifecycle journal; refusing recovery.')
    if pending and (pending['token'] != transaction['id'] or pending['uid'] != os.getuid()):
        raise ValueError('System and user deployment journals do not match.')
    if transaction['phase'] == 'committing':
        if pending:
            root(a, 'finish', transaction['id'])
        path.unlink()
        print('Completed the already validated deployment.')
        return
    if transaction['phase'] == 'applying':
        backup = Path(transaction['backup'])
        base = state_dir() / 'backups'
        if backup.is_symlink() or not backup.resolve().is_relative_to(base.resolve()):
            raise ValueError('Recovery backup must be inside Omadora backups.')
        if transaction['operation'] == 'install':
            rescue = a.restore_user(Path.home(), backup)
            a.desktop_settings('save', rescue)
            a.desktop_settings('restore', backup)
        # Upgrades never alter personal configuration; keep any edits made
        # during an interrupted upgrade instead of replacing them with copies.
        previous = transaction['previous']
        metadata = state_dir() / 'installation.json'
        if previous is None:
            metadata.unlink(missing_ok=True)
        else:
            atomic_json(metadata, previous)
        transaction['phase'] = 'restored'
        atomic_json(path, transaction)
    if pending:
        root(a, 'rollback', transaction['id'])
    targets = [p for p in (a.PREFIX, Path('/etc/pam.d/omarchy-lock-password'),
                            Path('/usr/share/wayland-sessions/omadora.desktop')) if p.exists()]
    if targets:
        a.run('sudo', 'restorecon', '-RF', *targets)
    if transaction['operation'] == 'install' and shutil.which('fc-cache'):
        a.run('fc-cache', '-f')
    path.unlink()
    print('Recovered desktop files and settings. Installed RPMs and enabled repositories were retained.')


def perform(a, operation):
    a.preflight()
    with locked(), tempfile.TemporaryDirectory(prefix='omadora-maintenance-') as temporary:
        # Keep the recovery helper alive even if rollback restores a legacy
        # desktop that predates this command, or deploy moves the active prefix.
        a._deploy_helper = Path(temporary) / 'omadora_deploy.py'
        shutil.copy2(a.ROOT / 'omadora_deploy.py', a._deploy_helper)
        offline(a)
        if operation == 'recover':
            return recover(a)
        ensure_ready(a)
        try:
            if operation == 'install':
                return a._install()
            if operation == 'rollback':
                return rollback(a)
            return upgrade_local(a)
        except (Exception, KeyboardInterrupt):
            if (state_dir() / 'transaction.json').exists():
                print('Deployment failed; restoring its snapshot.', file=sys.stderr)
                try:
                    recover(a)
                except (Exception, KeyboardInterrupt) as error:
                    print('Automatic recovery could not finish: ' + str(error) +
                          '\nRun the bootstrap with recover from GNOME or a TTY.', file=sys.stderr)
            raise


def upgrade_local(a):
    metadata = state_dir() / 'installation.json'
    if not a.PREFIX.is_dir() or a.PREFIX.is_symlink() or not metadata.is_file():
        raise ValueError('No managed Omadora installation found for this user.')
    if a.read_json(metadata).get('status') == 'installing':
        raise ValueError('Legacy partial install detected; restore its configuration backup before manual system cleanup.')
    # Refuse to replace administrator changes to shared entrypoints.
    for name in ('omadora', 'omadora-session'):
        path = Path('/usr/local/bin') / name
        if not path.is_symlink() or os.readlink(path) != str(a.PREFIX / 'bin' / name):
            raise ValueError('Modified or missing managed entrypoint: ' + str(path))
    for path in (Path('/etc/pam.d/omarchy-lock-password'), Path('/usr/share/wayland-sessions/omadora.desktop')):
        if path.is_symlink() or not path.is_file() or path.read_bytes() != (a.PREFIX / 'system' / path.name).read_bytes():
            raise ValueError('Modified or missing managed system file: ' + str(path))
    with tempfile.TemporaryDirectory(prefix='omadora-upgrade-') as temporary:
        temp = Path(temporary)
        a.fetch_upstream(temp / 'source')
        stage = a.assemble(temp / 'source', temp / 'stage')
        env = a.prepare_runtime(temp)
        transaction = prepare(a, 'upgrade')
        root(a, 'deploy', transaction['id'], stage)
        env.update(OMARCHY_PATH=str(a.PREFIX / 'upstream'), OMARCHY_THEME_HEADLESS='1',
                   PATH=f'{a.PREFIX}/bin:{a.PREFIX}/upstream/bin:' + os.environ['PATH'])
        a.run('Hyprland', '--verify-config', '--config', Path.home() / '.config/hypr/hyprland.lua', env=env)
        root(a, 'activate', transaction['id'])
        a.run('sudo', 'restorecon', '-RF', a.PREFIX, '/etc/pam.d/omarchy-lock-password', '/usr/share/wayland-sessions/omadora.desktop')
        commit(a, transaction)
    print('Desktop upgraded. Personal configuration and selected theme/font were preserved. Log into Omadora to use it.')


def upgrade(a, local=False, ref='main'):
    if local:
        return perform(a, 'upgrade')
    a.preflight()
    offline(a)
    if ref.startswith('-') or not ref.strip():
        raise ValueError('Invalid Git reference.')
    with tempfile.TemporaryDirectory(prefix='omadora-release-') as temporary:
        repo = Path(temporary) / 'repo'
        a.run('git', 'init', repo)
        a.run('git', '-C', repo, 'remote', 'add', 'origin', 'https://github.com/DanielCoffey1/omadora.git')
        a.run('git', '-C', repo, 'fetch', '--depth', '1', 'origin', ref)
        a.run('git', '-C', repo, 'checkout', '--detach', 'FETCH_HEAD')
        a.run('python3', repo / 'omadora.py', 'upgrade', '--local')


def rollback(a):
    if not (state_dir() / 'installation.json').is_file():
        raise ValueError('No installation metadata found for this user.')
    if not root(a, 'previous'):
        raise ValueError('No previous desktop snapshot is available.')
    with tempfile.TemporaryDirectory(prefix='omadora-rollback-') as temporary:
        transaction = prepare(a, 'rollback')
        root(a, 'revert', transaction['id'])
        env = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get('XDG_RUNTIME_DIR') or temporary,
                   OMARCHY_PATH=str(a.PREFIX / 'upstream'), OMARCHY_THEME_HEADLESS='1',
                   PATH=f'{a.PREFIX}/bin:{a.PREFIX}/upstream/bin:' + os.environ['PATH'])
        a.run('Hyprland', '--verify-config', '--config', Path.home() / '.config/hypr/hyprland.lua', env=env)
        a.run('sudo', 'restorecon', '-RF', a.PREFIX, '/etc/pam.d/omarchy-lock-password', '/usr/share/wayland-sessions/omadora.desktop')
        commit(a, transaction, revision(a.PREFIX))
    print('Previous desktop restored; personal configuration and Fedora packages were retained.')
