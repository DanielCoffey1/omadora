"""Exercise cancellation, rerun refusal, and maintenance in disposable Fedora."""
import hashlib
import json
from pathlib import Path
import subprocess

cli = ['/usr/local/bin/omadora']
results = []


def run(args, answer=None):
    p = subprocess.run(args, input=answer, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=600)
    print(p.stdout, flush=True)
    return p


# Kitty is not part of the core manifest, so declining its real DNF prompt
# must leave it absent and report a nonzero exit to the caller.
assert subprocess.run(['rpm', '-q', 'kitty'], stdout=subprocess.DEVNULL).returncode != 0
p = run(cli + ['app', 'install', 'kitty'], 'n\n')
assert p.returncode != 0
assert subprocess.run(['rpm', '-q', 'kitty'], stdout=subprocess.DEVNULL).returncode != 0
results.append('PASS: canceled DNF app install reported failure and installed nothing')

p = run(['python3', '/usr/local/share/omadora/omadora.py', 'install'])
assert p.returncode != 0 and 'already installed' in p.stdout
results.append('PASS: installation refused to overwrite an existing deployment')

root = Path('/usr/local/share/omadora')
def hashes():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}

before = hashes()
assert run(cli + ['update'], 'y\n' * 100).returncode == 0
assert before == hashes(), 'DNF update changed the pinned desktop deployment'
results.append('PASS: Fedora update command completed and retained pinned desktop files')
assert run(['flatpak', 'update', '--user', '-y']).returncode == 0
results.append('PASS: user Flatpak update command completed (empty app set in this fixture)')
Path('/tmp/omadora-maintenance.json').write_text(json.dumps(results, indent=2))
print('\n'.join(results), flush=True)
