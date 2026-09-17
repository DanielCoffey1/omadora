#!/usr/bin/python3
"""Root-side deployment journal. CLI paths are fixed, never read from user state."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        json.dump(value, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        temporary = f.name
    os.replace(temporary, path)
    if os.name == 'posix':
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


class Deployment:
    # A different root is only used by unprivileged unit tests, never by the CLI.
    def __init__(self, root=Path('/')):
        self.root = Path(root)
        self.prefix = self.root / 'usr/local/share/omadora'
        self.state = self.root / 'var/lib/omadora/transaction'
        self.journal = self.state / 'journal.json'
        self.previous = self.state.parent / 'previous'
        self.paths = [self.prefix] + [self.root / p for p in (
            'usr/local/bin/omadora', 'usr/local/bin/omadora-session',
            'etc/pam.d/omarchy-lock-password', 'usr/share/wayland-sessions/omadora.desktop')]

    def status(self):
        return json.loads(self.journal.read_text()) if self.journal.exists() else None

    def require(self, token, uid):
        state = self.status()
        if not state or state['token'] != token or state['uid'] != uid:
            raise ValueError('Deployment journal does not belong to this operation/user.')
        return state

    def begin(self, token, uid):
        if self.status():
            raise ValueError('An unfinished deployment exists. Run omadora recover first.')
        for name in ('.omadora-displaced', '.omadora-staged'):
            if os.path.lexists(self.prefix.with_name(name)):
                raise ValueError('Unexpected deployment staging path; refusing to overwrite it.')
        # No system paths have changed before the prepared journal is durable.
        remove(self.state)
        self.state.mkdir(parents=True, mode=0o700)
        state = {'token': token, 'uid': uid, 'phase': 'preparing', 'existed': []}
        atomic_json(self.journal, state)
        for index, path in enumerate(self.paths):
            exists = os.path.lexists(path)
            state['existed'].append(exists)
            if exists:
                copy(path, self.state / 'backup' / str(index))
        if hasattr(os, 'sync'):
            os.sync()
        state['phase'] = 'prepared'
        atomic_json(self.journal, state)

    def deploy(self, token, uid, stage):
        state = self.require(token, uid)
        if state['phase'] != 'prepared':
            raise ValueError('Deployment is not prepared; recover before retrying.')
        candidate = self.state / 'candidate'
        copy(Path(stage), candidate)
        for required in ('omadora.py', 'omadora_deploy.py', 'omadora_lifecycle.py',
                         'bin/omadora', 'bin/omadora-session', 'system/omadora.desktop',
                         'system/omarchy-lock-password'):
            if not (candidate / required).is_file():
                raise ValueError('Incomplete staged desktop: ' + required)
        # cp/shutil can retain source ownership when run as root; explicitly own
        # every runtime object. Never follow symlinks while changing ownership.
        if self.root == Path('/'):
            for path in [candidate, *candidate.rglob('*')]:
                os.chown(path, 0, 0, follow_symlinks=False)
                if not path.is_symlink():
                    path.chmod(path.stat().st_mode & 0o755)
        state['phase'] = 'applying'
        atomic_json(self.journal, state)
        self.prefix.parent.mkdir(parents=True, exist_ok=True)
        staged = self.prefix.with_name('.omadora-staged')
        if os.path.lexists(staged):
            raise ValueError('Unexpected staged desktop; recover before continuing.')
        copy(candidate, staged)
        if os.path.lexists(self.prefix):
            # /var and /usr may be separate filesystems: use a sibling for the
            # short rename window, with the independent backup in /var intact.
            displaced = self.prefix.with_name('.omadora-displaced')
            if os.path.lexists(displaced):
                raise ValueError('Unexpected displaced desktop; recover before continuing.')
            os.replace(self.prefix, displaced)
        os.replace(staged, self.prefix)
        for path in self.paths[1:-1]:
            temporary = path.with_name('.' + path.name + '.omadora-new')
            remove(temporary)
            temporary.parent.mkdir(parents=True, exist_ok=True)
            if path.parent.name == 'bin':
                temporary.symlink_to(self.prefix / 'bin' / path.name)
            else:
                copy(self.prefix / 'system' / path.name, temporary)
                temporary.chmod(0o644)
            os.replace(temporary, path)

    def activate(self, token, uid):
        state = self.require(token, uid)
        if state['phase'] != 'applying':
            raise ValueError('No candidate desktop to activate.')
        path = self.paths[-1]
        temporary = path.with_name('.omadora.desktop.omadora-new')
        remove(temporary)
        copy(self.prefix / 'system/omadora.desktop', temporary)
        temporary.chmod(0o644)
        os.replace(temporary, path)

    def rollback(self, token, uid):
        state = self.require(token, uid)
        if state['phase'] not in ('preparing', 'prepared'):
            # Snapshots stay untouched until every restore succeeds. Retrying
            # recovery after another interruption repeats these fixed targets.
            for index, existed in enumerate(state['existed']):
                if existed and not os.path.lexists(self.state / 'backup' / str(index)):
                    raise ValueError('Deployment backup is incomplete; refusing recovery.')
            state['phase'] = 'recovering'
            atomic_json(self.journal, state)
            for index, path in enumerate(self.paths):
                temporary = path.with_name('.' + path.name + '.omadora-restore')
                remove(temporary)
                if state['existed'][index]:
                    copy(self.state / 'backup' / str(index), temporary)
                remove(path)
                if state['existed'][index]:
                    os.replace(temporary, path)
        self.finish(token, uid, retain=False)

    def revert(self, token, uid):
        state = self.require(token, uid)
        previous = json.loads((self.previous / 'journal.json').read_text())
        if state['phase'] != 'prepared' or previous['uid'] != uid:
            raise ValueError('No previous desktop owned by this user is available.')
        for index, existed in enumerate(previous['existed']):
            if existed and not os.path.lexists(self.previous / 'backup' / str(index)):
                raise ValueError('Previous desktop snapshot is incomplete.')
        state['phase'] = 'applying'
        atomic_json(self.journal, state)
        for index, path in enumerate(self.paths):
            temporary = path.with_name('.' + path.name + '.omadora-restore')
            remove(temporary)
            if previous['existed'][index]:
                copy(self.previous / 'backup' / str(index), temporary)
            remove(path)
            if previous['existed'][index]:
                os.replace(temporary, path)

    def finish(self, token, uid, retain=True):
        state = self.require(token, uid)
        if retain and state['existed'] and state['existed'][0]:
            # Keep one previous desktop for problems discovered after login.
            # A repeat after interruption always copies from the intact journal.
            pending = self.previous.with_name('previous-new')
            remove(pending)
            copy(self.state / 'backup', pending / 'backup')
            atomic_json(pending / 'journal.json', state)
            remove(self.previous)
            os.replace(pending, self.previous)
        state['phase'] = 'finished'
        atomic_json(self.journal, state)
        self.cleanup()

    def cleanup(self):
        for suffix in ('.omadora-displaced', '.omadora-staged'):
            remove(self.prefix.with_name(suffix))
        remove(self.state)


def main():
    import fcntl
    if os.geteuid() != 0 or not os.environ.get('SUDO_UID'):
        raise ValueError('Deployment helper must be called through sudo by Omadora.')
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('begin', 'deploy', 'activate', 'revert', 'rollback', 'finish', 'status', 'previous'))
    parser.add_argument('token')
    parser.add_argument('--stage', type=Path)
    args = parser.parse_args()
    # Only fixed root-controlled paths can ever be removed/restored by this CLI.
    for path in (Path('/var/lib/omadora'), Path('/var/lib/omadora/transaction'),
                 Path('/usr/local/share'), Path('/usr/local/bin'),
                 Path('/etc/pam.d'), Path('/usr/share/wayland-sessions')):
        if path.is_symlink():
            raise ValueError('Deployment target must not be a symlink: ' + str(path))
    base = Path('/var/lib/omadora')
    base.mkdir(mode=0o700, exist_ok=True)
    os.chmod(base, 0o700)
    with (base / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        deployment = Deployment()
        if deployment.status() and deployment.status()['phase'] == 'finished':
            deployment.cleanup()
        if args.action == 'status':
            print(json.dumps(deployment.status()))
        elif args.action == 'previous':
            path = deployment.previous / 'journal.json'
            saved = json.loads(path.read_text()) if path.exists() else None
            if saved and saved['uid'] != int(os.environ['SUDO_UID']):
                raise ValueError('Previous desktop belongs to another user.')
            print(json.dumps(saved))
        else:
            kwargs = {'stage': args.stage} if args.action == 'deploy' else {}
            getattr(deployment, args.action)(args.token, int(os.environ['SUDO_UID']), **kwargs)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit('Omadora deployment: ' + str(error))
