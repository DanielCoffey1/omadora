"""Exercise the actual installed package picker without running a transaction."""
import json
from pathlib import Path
import sys
sys.path.insert(0, '/usr/local/share/omadora')
import omadora

selected = omadora.choose_packages(sys.argv[1])
Path('/tmp/omadora-vm-results/picker-' + sys.argv[1] + '.json').write_text(json.dumps(selected))
input('Press Enter to close this test window.')
