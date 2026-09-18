"""Fedora implementations of optional setup wizards; never run at base install."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import subprocess
import tempfile

import omadora_optional as opt


def deps(*packages):
    opt.run('sudo', 'dnf', 'install', *packages)


def source(key, destination):
    recipe = opt.recipes()[key]
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp) / 'download'
        opt.download(recipe, artifact)
        if recipe['kind'] == 'binary':
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact, destination / 'app')
            (destination / 'app').chmod(0o755)
        else:
            opt.unpack(artifact, destination, recipe.get('archive', 'tar'))


def prompt(text):
    value = input(text).strip()
    if not value:
        raise ValueError('Cancelled; no selection was provided')
    return value


def own_launcher(key, terminal=False):
    opt.launcher(key, opt.recipes()[key]['name'],
                 ['python3', str(opt.ROOT / 'omadora_optional.py'), 'launch', key], terminal)


def mise_environment(path):
    with opt.locked('mise'):
        if not opt.installed('mise'):
            opt.asset_install('mise', opt.recipes()['mise'])
    return dict(os.environ, MISE_DATA_DIR=str(path / 'data'),
                MISE_CONFIG_FILE=str(path / 'mise.toml'))


def runtime(key, path):
    # Exact versions are stored in the committed workflow recipe.
    if key == 'symfony':
        deps('php-cli', 'php-mbstring', 'php-xml', 'php-pdo', 'composer')
    elif key == 'scala':
        deps('java-devel', 'which')
    versions = opt.recipes()[key]['tools']
    env = mise_environment(path)
    opt.run(opt.location('mise') / 'mise', 'install', *versions, env=env)
    for command in opt.recipes()[key].get('commands', [key]):
        opt.command_link(key, command, [command])
    own_launcher(key, True)


def add_launcher(kind, path):
    registry = path / 'launchers.json'
    entries = json.loads(registry.read_text()) if registry.exists() else {}
    if kind == 'tui':
        name = prompt('Launcher name: ')
        command = shlex.split(prompt('Command and arguments (no shell evaluation): '))
        if not command or not shutil.which(command[0]):
            raise ValueError('Install the terminal application first')
        command = ['foot', *command]
    else:
        deps('flatpak')
        opt.run('flatpak', 'remote-add', '--user', '--if-not-exists', 'flathub', 'https://flathub.org/repo/flathub.flatpakrepo')
        opt.run('flatpak', 'install', '--user', 'flathub', 'org.libretro.RetroArch')
        game = Path(prompt('Path to your game/ROM: ')).expanduser().resolve(strict=True)
        core = Path(prompt('Path to a downloaded RetroArch core (.so): ')).expanduser().resolve(strict=True)
        name = prompt('Launcher name: ')
        command = ['flatpak', 'run', '--filesystem=' + str(game.parent) + ':ro',
                   '--filesystem=' + str(core.parent) + ':ro', 'org.libretro.RetroArch', '-L', str(core), str(game)]
    key = kind + '-' + hashlib.sha256(name.encode()).hexdigest()[:16]
    opt.launcher(key, name, command)
    entries[key] = name
    registry.write_text(json.dumps(entries))


def docker():
    # Fedora's Moby packages provide the Docker API expected by ONCE.
    deps('moby-engine', 'docker-cli', 'docker-compose')
    opt.run('sudo', 'systemctl', 'enable', '--now', 'docker.service')


def windows(path):
    deps('qemu-kvm', 'libvirt-daemon-kvm', 'libvirt-client', 'virt-install',
         'virt-viewer', 'edk2-ovmf', 'swtpm', 'swtpm-tools')
    if not os.access('/dev/kvm', os.R_OK | os.W_OK):
        raise ValueError('KVM is not accessible. Enable CPU virtualization and sign in again after installing virtualization packages.')
    storage = Path.home() / '.local/share/omadora-vms'
    storage.mkdir(parents=True, exist_ok=True)
    xml = storage / 'windows.xml'
    disk = storage / 'windows.qcow2'
    if xml.exists():
        opt.run('virsh', '--connect', 'qemu:///session', 'define', xml)
    else:
        if disk.exists():
            raise ValueError('Existing Windows disk retained. Import it with virt-manager instead of overwriting it.')
        iso = Path(prompt('Path to your licensed Windows installation ISO: ')).expanduser().resolve(strict=True)
        opt.run('virt-install', '--connect', 'qemu:///session', '--name', 'omadora-windows',
                '--memory', '8192', '--vcpus', '4', '--disk', f'path={disk},size=64,bus=sata',
                '--cdrom', iso, '--os-variant', 'win11', '--boot', 'uefi',
                '--tpm', 'backend.type=emulator,backend.version=2.0,model=tpm-crb',
                '--network', 'user,model=e1000e', '--graphics', 'spice', '--noautoconsole')
        xml.write_text(subprocess.check_output(['virsh', '--connect', 'qemu:///session', 'dumpxml', 'omadora-windows'], text=True))
    own_launcher('windows')
    print('Open Windows VM from the app launcher to finish the guest installation.')


DATABASES = {
    'postgres': ('docker.io/library/postgres:18', 5432, '/var/lib/postgresql', 'POSTGRES_PASSWORD'),
    'mysql': ('docker.io/library/mysql:8.4', 3306, '/var/lib/mysql', 'MYSQL_ROOT_PASSWORD'),
    'mariadb': ('docker.io/library/mariadb:11.8', 3306, '/var/lib/mysql', 'MARIADB_ROOT_PASSWORD'),
    'redis': ('docker.io/library/redis:7', 6379, '/data', None),
    'mongodb': ('docker.io/library/mongo:8', 27017, '/data/db', 'MONGO_INITDB_ROOT_PASSWORD'),
    'mssql': ('mcr.microsoft.com/mssql/server:2022-CU12-ubuntu-22.04', 1433, '/var/opt/mssql', 'MSSQL_SA_PASSWORD'),
}


def database(key, path):
    deps('podman')
    db = key.removeprefix('db-')
    image, port, mount, password_var = DATABASES[db]
    name = 'omadora-' + key
    envfile = Path.home() / '.config/omadora/databases' / (db + '.env')
    envfile.parent.mkdir(parents=True, exist_ok=True)
    if not envfile.exists():
        if db == 'mssql' and prompt('Accept Microsoft SQL Server Developer edition license terms? Type yes: ') != 'yes':
            raise ValueError('License terms were not accepted')
        values = [] if not password_var else [password_var + '=Oma9!' + secrets.token_urlsafe(24)]
        if db == 'mongodb':
            values.append('MONGO_INITDB_ROOT_USERNAME=admin')
        if db == 'mssql':
            values += ['ACCEPT_EULA=Y', 'MSSQL_PID=Developer']
        fd = os.open(envfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write('\n'.join(values) + '\n')
    existing = subprocess.run(['podman', 'container', 'exists', name], check=False).returncode
    if existing == 0:
        label = subprocess.check_output(['podman', 'inspect', '--format', '{{index .Config.Labels "org.omadora.recipe"}}', name], text=True).strip()
        if label != key:
            raise ValueError('Existing container is not owned by this installer: ' + name)
    elif existing == 1:
        opt.run('podman', 'pull', image)
        opt.run('podman', 'create', '--name', name, '--label', 'org.omadora.recipe=' + key, '--env-file', envfile,
                '--publish', f'127.0.0.1:{port}:{port}', '--volume', f'{name}-data:{mount}:Z', image)
    else:
        raise ValueError('Podman could not inspect the existing container')
    opt.run('podman', 'start', name)
    own_launcher(key, True)
    print(f'Local database on port {port}. Credentials: {envfile}. Named data volume is retained on removal.')


def install(key, path):
    if key == 'preinstalls':
        catalog = json.loads((opt.ROOT / 'apps.json').read_text())
        choices = [app_id + ' | ' + app['name'] for app_id, app in catalog.items() if app_id != key]
        result = subprocess.run(['gum', 'choose', '--no-limit', '--header', 'Select optional apps', *choices], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('App selection cancelled')
        for line in result.stdout.splitlines():
            app_id = line.split(' | ', 1)[0]
            if app_id not in catalog or app_id == key:
                raise ValueError('Unknown app selection')
            opt.run('python3', opt.ROOT / 'omadora.py', 'app', 'install', app_id)
    elif key in ('bun', 'deno', 'scala', 'symfony'):
        runtime(key, path)
    elif key.startswith('db-'):
        database(key, path)
    elif key in ('tui', 'retro-launcher'):
        add_launcher(key, path)
    elif key == 'copr-package':
        repository = prompt('COPR owner/project: ')
        packages = prompt('Package names separated by spaces: ').split()
        if not re.fullmatch(r'@?[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', repository) or any(
                not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]*', p) for p in packages):
            raise ValueError('Invalid repository or package names')
        opt.run('sudo', 'dnf', 'copr', 'enable', repository)
        opt.run('sudo', 'dnf', 'install', *packages)
        print('Use Remove → Fedora package for removal. COPR stays enabled for updates.')
    elif key == 'windows':
        windows(path)
    elif key == 'once':
        docker()
        source('once-binary', path / 'runtime')
        opt.run('sudo', 'install', '-Dm755', path / 'runtime/app', '/usr/local/libexec/omadora-once')
        unit = path / 'omadora-once.service'
        unit.write_text('[Unit]\nDescription=Omadora ONCE background tasks\nAfter=docker.service\n'
                        '[Service]\nEnvironment=ONCE_NO_SELF_UPDATE=1\nExecStart=/usr/local/libexec/omadora-once background run --namespace once\n'
                        'Restart=on-failure\n[Install]\nWantedBy=multi-user.target\n')
        opt.run('sudo', 'install', '-m644', unit, '/etc/systemd/system/omadora-once.service')
        opt.run('sudo', 'systemctl', 'daemon-reload')
        opt.run('sudo', 'systemctl', 'enable', '--now', 'omadora-once.service')
        own_launcher(key, True)
    elif key == 'xbox-cloud':
        deps('chromium')
        own_launcher(key)
    elif key == 'chromium-account':
        deps('chromium')
        own_launcher(key)
        print('Use the Chromium Account launcher. Google sign-in availability remains controlled by Google.')
    elif key == 'battlenet':
        deps('lutris', 'xrandr')
        own_launcher(key)
        opt.run('lutris', 'lutris:install/battlenet')
        print('Finish the Lutris installer. Games and Wine prefixes are managed by Lutris.')
    elif key == 'dictation':
        deps('wtype', 'pipewire-alsa')
        with opt.locked('voxtype-rpm'):
            opt.asset_install('voxtype-rpm', opt.recipes()['voxtype-rpm'])
        config = Path.home() / '.config/voxtype/config.toml'
        if not config.exists():
            config.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(opt.ROOT / 'upstream/default/voxtype/config.toml', config)
        opt.run('voxtype', 'setup', '--download', '--no-post-install')
        opt.run('voxtype', 'setup', 'systemd')
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            opt.run('hyprctl', 'reload')
            opt.run('omarchy-restart-shell')
    elif key == 'xbox-controllers':
        deps('dkms', 'make', 'gcc', 'bluez', 'bluez-tools', 'kernel-headers',
             'kernel-devel-' + os.uname().release, 'openssl', 'mokutil')
        source('xpadneo-source', path / 'source')
        tree = next((path / 'source').glob('xpadneo-*'))
        opt.run('sudo', str(tree / 'install.sh'), cwd=tree)
        print('Driver built. Secure Boot systems may need DKMS MOK enrollment and a reboot before pairing.')
        state = subprocess.run(['mokutil', '--sb-state'], capture_output=True, text=True)
        if 'enabled' in state.stdout.lower():
            print('Secure Boot is enabled. Enroll the DKMS certificate with sudo mokutil --import /var/lib/dkms/mok.pub, then approve it at reboot.')
        print('The existing xpad driver is preserved; no blanket driver blacklist or input-group access is added.')
    elif key == 'laravel':
        deps('php-cli', 'php-mbstring', 'php-xml', 'php-pdo', 'php-bcmath', 'composer', 'nodejs22', 'nodejs22-npm')
        env = dict(os.environ, COMPOSER_HOME=str(path / 'composer'))
        opt.run('composer', 'global', 'require', 'laravel/installer:' + opt.recipes()[key]['version'], env=env)
        opt.command_link(key, 'laravel')
        own_launcher(key, True)
    elif key == 'phoenix':
        deps('elixir', 'erlang-erts', 'gcc', 'make', 'nodejs22', 'nodejs22-npm')
        env = dict(os.environ, MIX_HOME=str(path / 'mix'), HEX_HOME=str(path / 'hex'))
        opt.run('mix', 'local.hex', '--force', env=env)
        opt.run('mix', 'local.rebar', '--force', env=env)
        opt.run('mix', 'archive.install', 'hex', 'phx_new', opt.recipes()[key]['version'], '--force', env=env)
        opt.command_link(key, 'omadora-phoenix')
        own_launcher(key, True)
    elif key == 'openclaw':
        deps('git', 'gcc-c++', 'make')
        env = mise_environment(path)
        tools = opt.recipes()[key]['tools']
        opt.run(opt.location('mise') / 'mise', 'install', *tools, env=env)
        opt.run(opt.location('mise') / 'mise', 'exec', *tools, '--', 'npm', 'install', '--prefix', path,
                '--no-fund', '--no-audit', 'openclaw@' + opt.recipes()[key]['version'], env=env)
        opt.command_link(key, 'openclaw')
        own_launcher(key, True)
        print('Open OpenClaw from the launcher to run its account/onboarding wizard.')
    elif key == 'hermes':
        deps('nodejs22', 'nodejs22-npm', 'git', 'python3-devel', 'gcc-c++', 'make', 'gtk3', 'nss', 'alsa-lib', 'libXScrnSaver')
        source('hermes-source', path / 'source')
        tree = next((path / 'source').glob('hermes-agent-*'))
        env = dict(os.environ, GITHUB_SHA='2237be355906fbe6065ce1815711eee52b2d646e', GITHUB_REF_NAME='main')
        opt.run('npm', 'ci', cwd=tree, env=env)
        opt.run('npm', 'run', 'pack', cwd=tree / 'apps/desktop', env=env)
        if not (tree / 'apps/desktop/release/linux-unpacked/Hermes').is_file():
            raise ValueError('Hermes build did not produce the expected desktop binary')
        own_launcher(key)
    else:
        raise ValueError('Unknown workflow: ' + key)


def launch(key, path, args):
    if key in ('bun', 'deno', 'scala', 'symfony'):
        recipe = opt.recipes()[key]
        command = recipe.get('commands', [key])[0]
        if args and args[0] in recipe.get('commands', []):
            command, args = args[0], args[1:]
        opt.run(opt.location('mise') / 'mise', 'exec', *recipe['tools'], '--', command, *args,
                env=mise_environment(path))
    elif key.startswith('db-'):
        opt.run('podman', 'start', 'omadora-' + key)
        opt.run('podman', 'logs', '--follow', 'omadora-' + key)
    elif key == 'windows':
        subprocess.run(['virsh', '--connect', 'qemu:///session', 'start', 'omadora-windows'], check=False)
        opt.run('virt-viewer', '--connect', 'qemu:///session', 'omadora-windows')
    elif key == 'once':
        opt.run('sudo', '/usr/local/libexec/omadora-once', *args)
    elif key in ('xbox-cloud', 'chromium-account'):
        binary = shutil.which('chromium-browser') or shutil.which('chromium')
        if not binary:
            raise ValueError('Chromium is missing')
        if key == 'xbox-cloud':
            opt.run(binary, '--app=https://www.xbox.com/play', *args)
        else:
            opt.run(binary, '--oauth2-client-id=77185425430.apps.googleusercontent.com',
                    '--oauth2-client-secret=OTJgUOQcT7lO7GsGZq2G4IlT', *args)
    elif key == 'battlenet':
        opt.run('lutris', 'lutris:rungame/battlenet')
    elif key == 'laravel':
        opt.run(path / 'composer/vendor/bin/laravel', *args,
                env=dict(os.environ, COMPOSER_HOME=str(path / 'composer')))
    elif key == 'phoenix':
        opt.run('mix', 'phx.new', *args, env=dict(os.environ, MIX_HOME=str(path / 'mix'), HEX_HOME=str(path / 'hex')))
    elif key == 'openclaw':
        command = path / 'node_modules/.bin/openclaw'
        if not args:
            args = ['dashboard'] if (Path.home() / '.openclaw/openclaw.json').is_file() else ['onboard', '--install-daemon']
        opt.run(opt.location('mise') / 'mise', 'exec', *opt.recipes()[key]['tools'], '--', command, *args,
                env=mise_environment(path))
    elif key == 'hermes':
        tree = next((path / 'source').glob('hermes-agent-*'))
        opt.run(tree / 'apps/desktop/release/linux-unpacked/Hermes', *args)


def remove(key, path):
    if key.startswith('db-'):
        name = 'omadora-' + key
        exists = subprocess.run(['podman', 'container', 'exists', name], check=False).returncode
        if exists == 0:
            label = subprocess.check_output(['podman', 'inspect', '--format', '{{index .Config.Labels "org.omadora.recipe"}}', name], text=True).strip()
            if label != key:
                raise ValueError('Refusing to remove an unowned container: ' + name)
            opt.run('podman', 'stop', name)
            opt.run('podman', 'rm', name)
        elif exists != 1:
            raise ValueError('Podman could not inspect the existing container')
    elif key in ('tui', 'retro-launcher'):
        registry = path / 'launchers.json'
        for item in json.loads(registry.read_text()) if registry.exists() else {}:
            desktop = Path.home() / '.local/share/applications' / ('omadora-' + item + '.desktop')
            if desktop.is_file() and not desktop.is_symlink() and 'X-Omadora-Managed=true' in desktop.read_text():
                desktop.unlink()
    elif key == 'once':
        opt.run('sudo', 'systemctl', 'disable', '--now', 'omadora-once.service')
        opt.run('sudo', 'rm', '--', '/etc/systemd/system/omadora-once.service', '/usr/local/libexec/omadora-once')
        opt.run('sudo', 'systemctl', 'daemon-reload')
    elif key == 'windows':
        state = subprocess.check_output(['virsh', '--connect', 'qemu:///session', 'domstate', 'omadora-windows'], text=True)
        if 'shut off' not in state:
            opt.run('virsh', '--connect', 'qemu:///session', 'shutdown', 'omadora-windows')
            raise ValueError('Windows is still running; retained VM and disk')
        opt.run('virsh', '--connect', 'qemu:///session', 'undefine', 'omadora-windows', '--keep-nvram', '--keep-tpm')
    elif key == 'dictation':
        subprocess.run(['systemctl', '--user', 'disable', '--now', 'voxtype.service'], check=False)
        opt.run('sudo', 'dnf', 'remove', 'voxtype')
    elif key == 'xbox-controllers':
        opt.run('sudo', 'dkms', 'remove', 'hid-xpadneo/' + opt.recipes()['xpadneo-source']['version'], '--all')
    elif key == 'openclaw':
        unit = Path.home() / '.config/systemd/user/openclaw-gateway.service'
        if unit.exists() and (path / 'node_modules/.bin/openclaw').exists():
            if str(path) not in unit.read_text():
                raise ValueError('Existing OpenClaw service belongs to another installation; retained it')
            launch(key, path, ['gateway', 'uninstall'])
    # Framework caches and dependencies in this managed tree are removed by
    # the caller. Project directories, app profiles and database data are not.
