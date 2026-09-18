"""Disposable Fedora checks for real optional downloads and user installs."""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, '/src')
import omadora_optional as opt
import omadora_workflows as workflows

key = sys.argv[1]
recipe = opt.recipes()[key]
if os.geteuid() == 0:
    packages = ['sudo', 'python3', 'bsdtar', 'zstd', 'fontconfig', 'binutils', 'file',
                'desktop-file-utils', 'git', *recipe.get('dependencies', [])]
    subprocess.run(['dnf', '-y', 'install', *packages], check=True)
    subprocess.run(['useradd', '-m', 'optional-test'], check=True)
    Path('/etc/sudoers.d/optional-test').write_text('optional-test ALL=(ALL) NOPASSWD: ALL\n')
    Path('/etc/sudoers.d/optional-test').chmod(0o440)
    raise SystemExit(subprocess.call(['sudo', '-iu', 'optional-test', 'python3', '/src/tests/optional-assets.py', key]))

original_run = opt.run
def noninteractive(*args, **kwargs):
    if tuple(str(x) for x in args[:2]) == ('sudo', 'dnf'):
        args = (*args[:2], '-y', *args[2:])
    return original_run(*args, **kwargs)
opt.run = noninteractive

root = opt.location(key)
root.parent.mkdir(parents=True, exist_ok=True)
if recipe['kind'] == 'workflow':
    root.mkdir()
    workflows.install(key, root)
    (root / 'installed.json').write_text(json.dumps({'recipe': recipe}))
    print('PASS: real workflow install', key, flush=True)
elif key.endswith('-source'):
    workflows.source(key, root)
    assert any(root.iterdir())
    print('PASS: verified source archive download and extraction', key, flush=True)
    raise SystemExit(0)
else:
    opt.asset_install(key, recipe)
assert opt.installed(key), key
if key in ('bun', 'deno', 'scala', 'symfony', 'laravel', 'openclaw'):
    workflows.launch(key, root, ['version'] if key == 'symfony' else ['--version'])
    if key == 'scala':
        for command in ('scalac', 'scala-cli'):
            workflows.launch(key, root, [command, '--version'])
    print('PASS: real command launch', key, flush=True)
elif key == 'phoenix':
    workflows.launch(key, root, ['--version'])
    print('PASS: Phoenix generator launch', flush=True)
elif key == 'mise':
    subprocess.run([root / recipe['executable'], '--version'], check=True)
elif key in ('codex', 'claude'):
    wrapper = Path.home() / '.local/bin' / key
    subprocess.run([wrapper, '--version'], check=True)
    subprocess.run([wrapper, '--help'], check=True, stdout=subprocess.DEVNULL)
    print('PASS: installed CLI wrapper version and help', key, flush=True)
desktop = Path.home() / '.local/share/applications' / ('omadora-' + key + '.desktop')
if desktop.exists():
    subprocess.run(['desktop-file-validate', desktop], check=True)
if recipe['kind'] == 'font':
    assert list(root.rglob('*.ttf')) or list(root.rglob('*.otf'))
elif recipe.get('executable'):
    executable = root / recipe['executable']
    assert executable.read_bytes()[:4] == b'\x7fELF'
    check = subprocess.run(['ldd', executable], capture_output=True, text=True)
    print(check.stdout)
    assert 'not found' not in check.stdout, check.stdout
print('PASS: pinned install, presence and desktop registration', key, flush=True)
# Test user data separately from package payload.
personal = Path.home() / '.config' / ('test-' + key)
personal.mkdir(parents=True, exist_ok=True)
(personal / 'keep').write_text('personal data')
if key in ('codex', 'claude'):
    profile = Path.home() / ('.' + key)
    profile.mkdir(exist_ok=True)
    (profile / 'omadora-test-preserve').write_text('keep profile')
opt.remove(key, recipe)
assert not opt.installed(key)
assert (personal / 'keep').read_text() == 'personal data'
if key in ('codex', 'claude'):
    assert (profile / 'omadora-test-preserve').read_text() == 'keep profile'
    assert not wrapper.exists()
print('PASS: removal retains personal files', key, flush=True)
