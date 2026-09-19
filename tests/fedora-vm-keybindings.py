"""Open the actual guide through both user entry points in a live Fedora desktop."""
import importlib.util
import json
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('interactions', Path(__file__).with_name('fedora-vm-interactions.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def guide():
    # Record the dependency that the original --print-only test never exercised.
    (v.OUT / 'perl-json-status.txt').write_text(v.guest("perl -MJSON::PP -e 1 2>&1; echo status=$?"))
    v.guest('omarchy-menu close')
    for entrypoint in ('shortcut', 'menu'):
        if entrypoint == 'shortcut':
            v.keys('meta_l', 'k')
        else:
            v.guest('omarchy-menu summon learn')
            time.sleep(1)
            for char in 'keybindings':
                v.keys(char)
            v.keys('ret')
        v.wait_for(lambda: v.guest("pgrep -af '[o]marchy-menu-select Keybindings'"), 20)
        v.wait_for(lambda: 'omarchy-menu' in v.guest('hyprctl layers -j'), 10)
        time.sleep(1)
        v.guest('grim /tmp/omadora-vm-results/keybindings-' + entrypoint + '.png')
        # Filtering and selecting a real binding must work, not just printing it.
        before = {c['address'] for c in json.loads(v.guest('hyprctl clients -j'))}
        for char in 'terminal':
            v.keys(char)
        time.sleep(1)
        v.guest('grim /tmp/omadora-vm-results/keybindings-' + entrypoint + '-filtered.png')
        v.keys('ret')
        v.wait_for(lambda: any(c['address'] not in before and c['class'].lower() == 'foot'
                              for c in json.loads(v.guest('hyprctl clients -j'))), 15)
        v.keys('meta_l', 'w')
    v.keys('meta_l', 'k')
    v.wait_for(lambda: v.guest("pgrep -af '[o]marchy-menu-select Keybindings'"), 20)
    v.keys('esc')
    v.wait_for(lambda: v.guest("pgrep -af '[o]marchy-menu-select Keybindings' >/dev/null; echo $?") == '1', 10)
    return 'Super+K and Learn → Keybindings opened; search and Terminal selection worked from each; Escape closed the guide.'


v.check('interactive keybindings guide', guide)
assert all(r['status'] == 'PASS' for r in v.results), v.results
